"""游戏自动演奏扩展。

读取 SRA 乐谱（JSON 格式，规范见 ``extensions/scores/README.md``），
将音符序列按节拍转换为游戏键盘按键（高八度 QWERTYU / 基本音 ASDFGHJ /
低八度 ZXCVBNM），并以绝对时间锚点调度保证音符间隔误差不超过 50ms。

运行方式::

    sra> extension run AutoPlayer

播放控制::

    F8  暂停/继续（可通过配置修改）
    F10 重置：回到乐谱开头重新演奏（可通过配置修改）
    F9  停止（SRA 全局停止热键）
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from pydantic import BaseModel, Field

from SRACore.extension import BaseExtension, extension
from SRACore.util.errors import ThreadStoppedError

# ── 乐谱常量 ──

SCORE_FORMAT = "sra-score"
SCORE_VERSION = 1
SCORE_DIR = Path(__file__).parent / "scores"

# 音名（科学音高记号）→ 游戏按键
PITCH_TO_KEY: dict[str, str] = {
    # 低八度
    "C3": "z", "D3": "x", "E3": "c", "F3": "v", "G3": "b", "A3": "n", "B3": "m",
    # 基本音（中八度）
    "C4": "a", "D4": "s", "E4": "d", "F4": "f", "G4": "g", "A4": "h", "B4": "j",
    # 高八度
    "C5": "q", "D5": "w", "E5": "e", "F5": "r", "G5": "t", "A5": "y", "B5": "u",
}
NOTE_KEYS = frozenset(PITCH_TO_KEY.values())
REST_PITCHES = frozenset({"rest", "r", ""})

_PITCH_RE = re.compile(r"^([A-G])([1-7])$")


class ScoreError(ValueError):
    """乐谱格式或内容错误。"""


# ── 乐谱数据模型与解析 ──

@dataclass
class Score:
    """解析后的乐谱。"""
    title: str
    bpm: float
    beat: str
    transpose: int
    notes: list["ScoreNote"]


@dataclass
class ScoreNote:
    """单个音符（乐谱层，尚未转换为按键）。"""
    index: int           # 1 起始序号，报错定位用
    pitches: list[str]   # 音名列表；空列表表示休止符
    duration: float      # 时值（拍数，四分音符 = 1）


@dataclass(frozen=True)
class NoteEvent:
    """时间轴上的单个演奏事件。"""
    index: int
    start_sec: float          # 相对乐谱起点的开始时刻（秒）
    end_sec: float            # 相对乐谱起点的结束时刻（秒）
    keys: tuple[str, ...]     # 映射后的按键（多键为和弦）
    label: str                # 展示用音名（如 "C4+E4"）


def resolve_score_path(score: str) -> Path:
    """将乐谱名称或路径解析为实际 JSON 文件路径。

    支持绝对/相对路径或乐谱名（自动在 ``extensions/scores/`` 下查找，
    可省略 ``.json`` 后缀）。
    """
    raw = Path(score.strip())
    candidates = [raw] if raw.is_absolute() else [raw, SCORE_DIR / raw]
    for cand in candidates:
        path = cand if cand.suffix == ".json" else cand.with_suffix(".json")
        if path.is_file():
            return path
    available = sorted(p.stem for p in SCORE_DIR.glob("*.json"))
    raise ScoreError(
        f"找不到乐谱 {score!r}；extensions/scores/ 下可用乐谱：{', '.join(available) or '（无）'}"
    )


def load_score(score: str) -> Score:
    """从名称或路径加载并解析乐谱。"""
    path = resolve_score_path(score)
    logger.debug(f"加载乐谱：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ScoreError(f"乐谱 {path.name} 不是有效的 JSON：{e}") from e
    return parse_score(data)


def parse_score(data: Any) -> Score:
    """解析并校验乐谱 JSON 数据，不符合规范时抛出 :class:`ScoreError`。"""
    if not isinstance(data, dict):
        raise ScoreError("乐谱根节点必须是 JSON 对象")
    if data.get("format") != SCORE_FORMAT:
        raise ScoreError(f'缺少 "format": "{SCORE_FORMAT}" 字段或值不正确')
    if data.get("version") != SCORE_VERSION:
        raise ScoreError(f"乐谱版本不支持：{data.get('version')!r}（当前支持 {SCORE_VERSION}）")

    meta = data.get("meta")
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise ScoreError('"meta" 必须是对象')
    title = str(meta.get("title") or "未命名")
    bpm = meta.get("bpm", 100)
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not 20 <= bpm <= 300:
        raise ScoreError(f'"meta.bpm" 必须是 20-300 的数值，当前为 {bpm!r}')
    beat = str(meta.get("beat") or "4/4")
    transpose = meta.get("transpose", 0)
    if not isinstance(transpose, int) or not -2 <= transpose <= 2:
        raise ScoreError('"meta.transpose" 必须是 -2~2 的整数（单位：八度）')

    raw_notes = data.get("notes")
    if not isinstance(raw_notes, list) or not raw_notes:
        raise ScoreError('"notes" 必须是非空数组')

    notes = [_parse_note(item, index) for index, item in enumerate(raw_notes, start=1)]
    return Score(title=title, bpm=float(bpm), beat=beat, transpose=transpose, notes=notes)


def _parse_note(item: Any, index: int) -> ScoreNote:
    where = f"第 {index} 个音符"
    if not isinstance(item, dict):
        raise ScoreError(f"{where} 必须是对象")

    duration = item.get("duration", 1.0)
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        raise ScoreError(f'{where} 的 "duration" 必须是正数（单位：拍），当前为 {duration!r}')

    pitch = item.get("pitch")
    if pitch is None or (isinstance(pitch, str) and pitch.strip().lower() in REST_PITCHES):
        return ScoreNote(index=index, pitches=[], duration=float(duration))
    raw_pitches = pitch if isinstance(pitch, list) else [pitch]
    if not raw_pitches:
        raise ScoreError(f'{where} 的 "pitch" 数组不能为空')
    pitches = []
    for raw in raw_pitches:
        if not isinstance(raw, str):
            raise ScoreError(f"{where} 的音名必须是字符串，当前为 {raw!r}")
        name = raw.strip().upper()
        if not _PITCH_RE.match(name):
            raise ScoreError(f'{where} 音名 {raw!r} 无效，需为 C3~B5 范围内的自然音（如 C4、A5）或 "rest"')
        pitches.append(name)
    return ScoreNote(index=index, pitches=pitches, duration=float(duration))


def resolve_pitch_key(pitch: str, transpose: int = 0, index: int = 0) -> str:
    """将音名（可整体移调）映射为游戏按键。"""
    match = _PITCH_RE.match(pitch)
    if match is None:
        raise ScoreError(f"第 {index} 个音符音名 {pitch!r} 无效")
    letter, octave = match.group(1), int(match.group(2)) + transpose
    if not 3 <= octave <= 5:
        raise ScoreError(f"第 {index} 个音符 {pitch} 移调 {transpose:+d} 八度后超出 C3~B5 范围")
    key = PITCH_TO_KEY.get(f"{letter}{octave}")
    if key is None:
        raise ScoreError(f"第 {index} 个音符 {pitch} 无法映射到游戏按键")
    return key


def build_timeline(score: Score, *, beat_sec: float) -> list[NoteEvent]:
    """将乐谱展开为按时间排序的演奏事件序列。

    Args:
        beat_sec: 单拍时长（秒），已包含演奏速度倍率。
    """
    events: list[NoteEvent] = []
    cursor = 0.0
    for note in score.notes:
        dur_sec = note.duration * beat_sec
        if note.pitches:
            keys = tuple(resolve_pitch_key(p, score.transpose, note.index) for p in note.pitches)
            events.append(NoteEvent(
                index=note.index,
                start_sec=cursor,
                end_sec=cursor + dur_sec,
                keys=keys,
                label="+".join(note.pitches),
            ))
        cursor += dur_sec
    return events


# ── 配置 ──

class AutoPlayerConfig(BaseModel):
    """自动演奏扩展配置。"""
    score: str = Field(default="远航星的告别", description="乐谱名称或 JSON 文件路径")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="演奏速度倍率（1.0 = 乐谱原速）")
    loop: int = Field(default=1, ge=1, le=99, description="演奏遍数")
    start_delay: float = Field(default=2.0, ge=0.0, le=30.0, description="首次开始前的延迟（秒），用于切换到游戏窗口")
    dry_run: bool = Field(default=False, description="演练模式：不实际按键，仅校验乐谱与时序")
    enable_hotkeys: bool = Field(default=True, description="启用演奏热键（暂停/重置）")
    hotkey_pause: str = Field(default="f8", description="暂停/继续热键")
    hotkey_reset: str = Field(default="f10", description="重置热键")


# ── 演奏引擎 ──

class _ResetSignal(Exception):
    """内部信号：热键请求从头重新演奏。"""


@dataclass
class PlayStats:
    """演奏统计信息。"""
    total_notes: int = 0
    notes_played: int = 0
    passes: int = 0
    resets: int = 0
    error_ms: list[float] = field(default_factory=list)

    def summary(self) -> str:
        if self.error_ms:
            errors = [abs(e) for e in self.error_ms]
            avg = sum(errors) / len(errors)
            timing = f"按键时序误差：平均 {avg:.1f}ms / 最大 {max(errors):.1f}ms"
        else:
            timing = "无时序采样"
        return f"音符 {self.notes_played}/{self.total_notes} × {self.passes} 遍，重置 {self.resets} 次，{timing}"


class _high_precision_timer:
    """Windows 下将系统定时器精度临时提升到 1ms（timeBeginPeriod）。

    默认 15.6ms 的定时器分辨率会让 ``time.sleep`` 出现最大约 15ms 的
    超额睡眠；提升精度后配合短程自旋可将音符误差控制在数毫秒以内。
    """

    def __enter__(self):
        self._active = False
        if sys.platform == "win32":
            try:
                import ctypes
                if ctypes.windll.winmm.timeBeginPeriod(1) == 0:
                    self._active = True
            except Exception as e:
                logger.debug(f"提升定时器精度失败（不影响功能）：{e}")
        return self

    def __exit__(self, *exc_info) -> bool:
        if self._active:
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        return False


class PlaybackEngine:
    """基于绝对时间锚点的演奏引擎。

    所有音符的目标时刻都由 ``锚点 + 音符偏移`` 独立计算，单个音符的
    执行耗时不会累积到后续音符；暂停期间锚点自动顺延，保证恢复后
    从暂停处继续且节奏不失真。

    支持的播放控制：暂停/继续（:meth:`toggle_pause`）、停止（通过
    ``stop_event`` 触发 :class:`ThreadStoppedError`）、重置（:meth:`reset`）。
    """

    def __init__(self, timeline: list[NoteEvent], *,
                 press: Callable[[str], bool],
                 stop_event: threading.Event | None,
                 loop: int = 1,
                 start_delay: float = 0.0,
                 dry_run: bool = False):
        self._timeline = timeline
        self._press = press
        self._stop_event = stop_event or threading.Event()
        self._loop = max(1, loop)
        self._start_delay = max(0.0, start_delay)
        self._dry_run = dry_run
        self._paused = threading.Event()
        self._reset_flag = threading.Event()
        self._pause_started: float | None = None
        self._pause_extra = 0.0

    # ── 播放控制（可从热键线程调用） ──

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def toggle_pause(self) -> bool:
        """切换暂停状态，返回切换后是否处于暂停。"""
        if self._paused.is_set():
            self.resume()
        else:
            self.pause()
        return self._paused.is_set()

    def reset(self) -> None:
        """请求重置：中断当前演奏并从乐谱开头重新开始。"""
        self._reset_flag.set()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    # ── 主流程 ──

    def play(self) -> PlayStats:
        """阻塞式演奏，直到完成全部遍数、被重置结束或线程被停止。"""
        self._reset_flag.clear()
        self._paused.clear()
        self._pause_started = None
        self._pause_extra = 0.0
        stats = PlayStats(total_notes=len(self._timeline))
        first_pass = True
        with _high_precision_timer():
            while True:
                try:
                    self._play_pass(stats, first_pass)
                    first_pass = False
                    stats.passes += 1
                    if stats.passes >= self._loop:
                        break
                except _ResetSignal:
                    first_pass = False
                    self._reset_flag.clear()
                    self._paused.clear()
                    self._pause_started = None
                    self._pause_extra = 0.0
                    stats.resets += 1
                    logger.info("演奏已重置，从头开始")
        return stats

    def _play_pass(self, stats: PlayStats, with_delay: bool) -> None:
        delay = self._start_delay if with_delay else 0.0
        anchor = time.perf_counter() + delay
        if delay > 0:
            logger.info(f"{delay:.1f} 秒后开始演奏，请切换到游戏窗口…")
        self._wait_until(anchor)
        for note in self._timeline:
            self._wait_until(anchor + note.start_sec)
            actual = time.perf_counter()
            stats.error_ms.append((actual - (anchor + note.start_sec + self._pause_extra)) * 1000)
            self._perform(note)
            stats.notes_played += 1

    def _wait_until(self, base_target: float) -> None:
        """精确等待到 ``base_target + 暂停补偿`` 时刻。

        - 粗等待阶段使用 ``stop_event.wait`` 休眠，可被停止事件立即打断；
        - 最后约 4ms 自旋等待，保证毫秒级精度；
        - 暂停期间记录时长，恢复后将锚点整体顺延。
        """
        while True:
            self._check_flags()
            if self._paused.is_set():
                if self._pause_started is None:
                    self._pause_started = time.perf_counter()
                self._stop_event.wait(0.05)
                continue
            if self._pause_started is not None:
                self._pause_extra += time.perf_counter() - self._pause_started
                self._pause_started = None
            target = base_target + self._pause_extra
            remaining = target - time.perf_counter()
            if remaining <= 0:
                return
            if remaining > 0.03:
                # 可被停止事件打断的粗略等待
                if self._stop_event.wait(min(remaining - 0.02, 0.25)):
                    self._check_flags()
            elif remaining > 0.004:
                time.sleep(remaining - 0.002)
            else:
                # 最后 ~4ms 自旋，保证精度
                while time.perf_counter() < target:
                    self._check_flags()
                return

    def _check_flags(self) -> None:
        if self._stop_event.is_set():
            raise ThreadStoppedError("演奏中断", "线程已停止")
        if self._reset_flag.is_set():
            raise _ResetSignal()

    def _perform(self, note: NoteEvent) -> None:
        if self._dry_run:
            logger.debug(f"[dry-run] 音符#{note.index} {note.label} @{note.start_sec:.3f}s")
            return
        # 瞬时敲击；和弦通过组合键同时触发
        if not self._press("+".join(note.keys)):
            logger.warning(f"音符#{note.index} 按键失败：{note.label}")


# ── 演奏热键 ──

class _HotkeyController:
    """演奏热键控制器：使用宿主（CLI）创建并注入的全局监听器单例。

    仅通过 ``register_key_event`` / ``unregister_key_event`` 操作按键
    注册表；监听线程的创建与销毁由宿主负责，扩展侧不调用
    ``start()`` / ``stop()``，演奏结束后只注销按键。
    """

    def __init__(self, listener, engine: PlaybackEngine, pause_key: str, reset_key: str):
        self._listener = listener
        self._engine = engine
        self._pause_key = pause_key.strip().lower()
        self._reset_key = reset_key.strip().lower()

    def start(self) -> None:
        for name in (self._pause_key, self._reset_key):
            if name in NOTE_KEYS:
                logger.warning(f"热键 {name!r} 与演奏按键冲突，演奏期间触发该键会同时控制播放，建议修改配置")
        self._listener.register_key_event(self._pause_key, self._on_pause)
        self._listener.register_key_event(self._reset_key, self._on_reset)
        logger.info(
            f"演奏热键已启用：暂停/继续 [{self._pause_key.upper()}]，"
            f"重置 [{self._reset_key.upper()}]（停止请按 SRA 全局停止键）"
        )

    def stop(self) -> None:
        self._listener.unregister_key_event(self._pause_key)
        self._listener.unregister_key_event(self._reset_key)

    def _on_pause(self, *_args) -> None:
        if self._engine.toggle_pause():
            logger.info("演奏已暂停（按暂停键继续）")
        else:
            logger.info("演奏继续")

    def _on_reset(self, *_args) -> None:
        self._engine.reset()


# ── 扩展入口 ──

@extension(name="自动演奏", description="按 JSON 乐谱自动演奏游戏键盘（暂停 F8 / 重置 F10 / 停止 F9）")  # pyright: ignore[reportArgumentType]
class AutoPlayerExtension(BaseExtension[AutoPlayerConfig]):
    """游戏自动演奏扩展。"""

    def run(self) -> bool:
        cfg = self.config

        try:
            score = load_score(cfg.score)
        except ScoreError as e:
            logger.error(f"乐谱加载失败：{e}")
            return False

        effective_bpm = score.bpm * cfg.speed
        beat_sec = 60.0 / effective_bpm
        timeline = build_timeline(score, beat_sec=beat_sec)
        if not timeline:
            logger.error("乐谱没有任何可演奏音符（全部为休止符）")
            return False
        total_sec = max(e.end_sec for e in timeline)

        logger.info(
            f"乐谱《{score.title}》：{len(timeline)} 个音符 / {score.beat} 拍 / "
            f"BPM {score.bpm:g} × {cfg.speed:g} = {effective_bpm:g}，"
            f"单遍时长约 {total_sec:.1f} 秒，演奏 {cfg.loop} 遍"
            + ("（演练模式，不实际按键）" if cfg.dry_run else "")
        )

        operator = self.operator
        engine = PlaybackEngine(
            timeline,
            press=lambda key: operator.press_key(key, trace=False),
            stop_event=operator.stop_event,
            loop=cfg.loop,
            start_delay=cfg.start_delay,
            dry_run=cfg.dry_run,
        )
        hotkeys = None
        if cfg.enable_hotkeys and not cfg.dry_run:
            if self.event_listener is None:
                logger.warning("未注入全局事件监听器，演奏热键（暂停/重置）不可用")
            else:
                hotkeys = _HotkeyController(
                    self.event_listener, engine, cfg.hotkey_pause, cfg.hotkey_reset)
                hotkeys.start()
        try:
            stats = engine.play()
        finally:
            if hotkeys is not None:
                hotkeys.stop()

        logger.info(f"演奏结束：《{score.title}》 {stats.summary()}")
        worst = max((abs(e) for e in stats.error_ms), default=0.0)
        if worst > 50.0:
            logger.warning(f"最大时序误差 {worst:.1f}ms 超过 50ms 目标，建议降低演奏速度或关闭其他高负载程序")
        return True
