"""按最新版攻略列表的方式读取扩展自有攻略，供配置窗口按需扫描。"""
import json
from pathlib import Path

from .paths import STRATEGY_ROOT


# ssyb：标题仅作显示，列表值始终对应实际攻略文件。
def scan_strategy_options(directory: Path | None = None):
    """每次请求重新读取 JSON 标题；单个无效文件不影响其他攻略显示。"""
    directory = Path(directory) if directory is not None else STRATEGY_ROOT
    try:
        paths = sorted(directory.iterdir(), key=lambda path: path.name.casefold())
    except OSError:
        return []
    options = []
    for path in paths:
        if path.suffix.lower() != ".json":
            continue
        try:
            if not path.is_file():
                continue
            # 与运行时攻略指纹的大小限制一致，避免配置窗口读取异常大文件。
            if path.stat().st_size > 1024 * 1024:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            title = data.get("title")
            label = title.strip() if isinstance(title, str) and title.strip() else path.stem
            options.append((path.stem, label))
        except (OSError, UnicodeError, ValueError):
            continue
    # 相同标题以文件名区分；保存的仍是原来的攻略文件名，不写入显示标题。
    labels = [label for _, label in options]
    return [(value, f"{label}（{value}）" if labels.count(label) > 1 else label)
            for value, label in options]
