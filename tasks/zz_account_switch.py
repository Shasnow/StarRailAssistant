"""SRA 账号切号插件（免密码）v2.6.2。

放入 SRA 的 tasks/ 目录即生效。目标账号来源按优先级：
1. AUTO-MAS 花名册：被 MAS 拉起时从命令行的 sra-config 路径反查
   config/ScriptConfig.json，解密该用户 Info.Id 作为目标账号。
2. account_hint.txt（手动跑 SRA 时兜底）：支持脱敏片段/完整手机号/邮箱。

切号动作：登录页点账号框触发历史账号下拉 → 选目标号 → 确认登录，
密码始终留在客户端本地。登出走电源图标路线（ESC → 手机菜单电源 →
确认返回登录页面），不触碰登录记录。

UID 终验：SRA 根目录 zz_uid_map.txt 每行「用户名或账号=游戏内UID」，
进游戏后 OCR 左下角 UID 比对，不符自动登出重切（最多 2 次）；插件
登录的会话会自动把 UID 记入映射表。
"""
import base64
import ctypes
import json
import re
import sys
import time
from pathlib import Path

from SRACore.util import encryption
from SRACore.util.logger import logger

try:
    from tasks.StartGameTask import LoginStatus, StartGameTask
except Exception as e:
    logger.warning(f"[切号] 加载 StartGameTask 失败，插件未启用: {e}")
    StartGameTask = None
    LoginStatus = None

try:
    from tasks.img import IMG, MAIMG
except Exception:
    try:
        from tasks.img import IMG
        MAIMG = None
    except Exception:
        IMG = None
        MAIMG = None

_ACCT_PAT = re.compile(r"\d{2,4}\*{2,}\d{2,4}")
_MAIL_PAT = re.compile(r"[A-Za-z0-9._-]+\*+[A-Za-z0-9._-]*@[A-Za-z0-9.-]+")
_VERIFIED_TTL = 900  # 已核对标记有效期（秒）

_MAS_TARGET = ""
_MAS_USER = ""  # 花名册用户名，zz_uid_map.txt 的优先键
_MAS_RESOLVED = False
_FLOW_LOGGED_AT = 0.0  # 插件本次登录的时间戳；0=非插件登录
_FLOW_WINDOW = 600  # fresh 判定窗口（秒）：hint 手动路径在切号前打点，最坏需覆盖
# 切号+等进游戏+UID 读取全程（约 375s），防时间戳残留导致跨任务误判


def _load_hint() -> str:
    p = Path(__file__).resolve().parent.parent / "account_hint.txt"
    try:
        return p.read_text(encoding="utf-8-sig").strip()
    except Exception:
        return ""


def _norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", s or "")


def _mask_acct(acct: str) -> str:
    """账号打码只露后 2 位（日志常被贴进 issue，不出现明文）"""
    a = acct or ""
    return "*" * max(len(a) - 2, 3) + a[-2:]


def _mask_text(s: str) -> str:
    """OCR 候选等自由文本打码：≥5 位数字串只露后 2 位，邮箱本地段打码"""
    s = re.sub(r"\d{5,}", lambda m: "*" * (len(m.group()) - 2) + m.group()[-2:], s or "")
    if "@" in s:
        s = re.sub(r"([A-Za-z0-9._%-])[A-Za-z0-9._%*-]{2,}@", r"\1***@", s)
    return s


def _split_mask(s: str):
    """提取「前缀数字+星号+后缀数字」掩码段，无则 None"""
    m = re.search(r"(\d{2,4})\*{2,}(\d{2,4})", s or "")
    return (m.group(1), m.group(2)) if m else None


def _match(hint: str, raw: str) -> bool:
    """账号匹配：归一化子串比对；掩码走双向 前缀+后缀 比对
    （登录页脱敏为前3+星+后2，配置常为后3位，同一号码两种显示）"""
    h, t = _norm(hint), _norm(raw)
    if not h or not t:
        return False
    # 纯子串分支要求双方 ≥5 位：排除「7分钟前」等短数字串误命中
    if len(h) >= 5 and len(t) >= 5 and (h in t or t in h):
        return True
    hm, rm = _split_mask(hint), _split_mask(raw)
    if hm and rm:
        pre_ok = hm[0] == rm[0] or hm[0].startswith(rm[0]) or rm[0].startswith(hm[0])
        suf_ok = hm[1].endswith(rm[1]) or rm[1].endswith(hm[1])
        if pre_ok and suf_ok:
            return True
    m = re.search(r"(\d{2,4})\*{2,}(\d{2,4})", raw)  # 页面掩码 vs 纯数字提示词
    if m and h.isdigit():
        pre, suf = m.group(1), m.group(2)
        if len(h) >= len(pre) + len(suf) and h.startswith(pre) and h.endswith(suf):
            return True
    m = _MAIL_PAT.search(raw)  # qin***@qq.com
    if m and "@" in (hint or ""):
        local, domain = m.group(0).split("@", 1)
        pre = _norm(local.split("*")[0])
        suf = _norm(domain)  # _norm 会去掉 @，加不加都一样
        if pre and suf and h.startswith(pre) and h.endswith(suf):
            return True
    return False


def _mas_context():
    """从命令行找 MAS 下发的临时配置路径 → (MAS根目录, 用户uid)"""
    for arg in sys.argv:
        if "sra-config" not in arg.lower():
            continue
        m = re.search(r'[A-Za-z]:\\[^"]+\.json', arg)
        if not m:
            continue
        parts = Path(m.group(0)).parts
        low = [p.lower() for p in parts]
        if "sra-config" not in low:
            continue
        i = low.index("sra-config")
        if i >= 2 and low[i - 1] == "hsr" and low[i - 2] == "data" and len(parts) >= i + 3:
            root = Path(*parts[: i - 2])
            if (root / "config" / "ScriptConfig.json").is_file():
                return root, parts[i + 2]
    return None


def _find_user(node, uid):
    """在 ScriptConfig.json 里递归找 uid 对应的用户 Info 节点"""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == uid and isinstance(v, dict) and isinstance(v.get("Info"), dict):
                return v["Info"]
            r = _find_user(v, uid)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _find_user(v, uid)
            if r is not None:
                return r
    return None


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.c_void_p)]


def _dpapi_decrypt(b64s: str) -> str:
    blob = base64.b64decode(b64s)
    bufin = _DATA_BLOB(len(blob), ctypes.cast(blob, ctypes.c_void_p))
    bout = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(bufin), None, None, None, None, 0, ctypes.byref(bout)
    ):
        raise OSError("CryptUnprotectData 失败")
    try:
        return ctypes.string_at(bout.pbData, bout.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.c_void_p(bout.pbData))


def _decrypt_mas_id(enc: str) -> str:
    enc = (enc or "").strip()
    if not enc:
        return ""
    if not enc.startswith("AQAA"):  # 非 DPAPI 密文视为明文
        return enc
    try:
        v = encryption.decryptor(enc)
        if v:
            return v
    except Exception:
        pass
    try:
        return _dpapi_decrypt(enc)
    except Exception:
        return ""


def _mas_target() -> str:
    """花名册目标账号，每进程只解析一次；非 MAS 拉起返回空"""
    global _MAS_TARGET, _MAS_USER, _MAS_RESOLVED
    if _MAS_RESOLVED:
        return _MAS_TARGET
    _MAS_RESOLVED = True
    try:
        ctx = _mas_context()
        if ctx is None:
            return ""
        root, uid = ctx
        cfg = json.loads((root / "config" / "ScriptConfig.json").read_text(encoding="utf-8"))
        info = _find_user(cfg, uid)
        if info is None:
            logger.warning("[切号] 花名册中未找到当前用户，跳过切号")
            return ""
        name = info.get("Name", "?")
        acct = _decrypt_mas_id(info.get("Id", ""))
        if not acct:
            logger.warning(f"[切号] 用户「{name}」账号为空或解密失败，跳过切号")
            return ""
        logger.info(f"[切号] 目标账号 {name} {_mask_acct(acct)}")
        _MAS_TARGET = acct
        _MAS_USER = name
    except Exception as e:
        logger.warning(f"[切号] 读取花名册失败，跳过切号: {e}")
    return _MAS_TARGET


def _mark_verified(self, target: str) -> None:
    """记「已核对=目标号」标记（类属性跨实例可见）及插件登录时间戳"""
    try:
        type(self)._zz_verified = (target, time.time())
        global _FLOW_LOGGED_AT
        _FLOW_LOGGED_AT = time.time()
    except Exception:
        pass


def _clear_verified(self) -> None:
    try:
        type(self)._zz_verified = None
    except Exception:
        pass


def _check_verified(self, target: str) -> bool:
    """游戏已在主界面时，判断会话是否为刚核对放行过的目标号"""
    try:
        mark = getattr(type(self), "_zz_verified", None)
        if mark and mark[0] == target and time.time() - mark[1] <= _VERIFIED_TTL:
            return True
    except Exception:
        pass
    return False


def _wait_entered(self) -> int:
    if self.operator.wait_ocr_any(
        ["欢迎", "开始游戏", "点击进入"], from_x=0.44, from_y=0.07, to_x=0.6, to_y=0.9, timeout=180
    ):
        return 1
    logger.warning("[切号] 登录后等待进入游戏超时")
    return -1


def _load_uid_map() -> dict:
    """读 zz_uid_map.txt：每行「用户名或账号=UID」，# 注释"""
    p = Path(__file__).resolve().parent.parent / "zz_uid_map.txt"
    try:
        out = {}
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), re.sub(r"\D", "", v)
            if k and v:
                out[k] = v
        return out
    except Exception:
        return {}


def _target_uid(target: str, umap=None) -> str:
    """查目标 UID：优先花名册用户名，其次账号字符串；umap 可传入已读映射表"""
    m = _load_uid_map() if umap is None else umap
    if not m:
        return ""
    if _MAS_USER and _MAS_USER in m:
        return m[_MAS_USER]
    for k, v in m.items():
        if _match(k, target) or _match(target, k):
            return v
    return ""


def _read_game_uid(self, timeout: float = 15) -> str:
    """OCR 主界面左下角 UID（如 UID:123456789），读不到返回空"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for b in (self.operator.ocr_boxes() or []):
            m = re.search(r"UID\s*[:：]?\s*(\d{6,10})", b.source or "", re.I)
            if m:
                return m.group(1)
        self.operator.sleep(2)
    return ""


def _uid_owner(uid: str, umap=None) -> str:
    """查 UID 在映射表中的归属键，未见过的 UID 返回空；umap 可传入已读映射表"""
    for k, v in (_load_uid_map() if umap is None else umap).items():
        if v == uid:
            return k
    return ""


def _record_uid(self, target: str, got: str) -> None:
    """把 UID 自动写入 zz_uid_map.txt（键优先花名册用户名）；
    已有条目值不同只报错不覆盖，防错号污染映射表"""
    global _FLOW_LOGGED_AT
    key = _MAS_USER or target
    p = Path(__file__).resolve().parent.parent / "zz_uid_map.txt"
    try:
        if p.is_file():
            lines = p.read_text(encoding="utf-8-sig").splitlines()
        else:
            lines = [
                "# UID 终验映射表（插件自动维护，也可手工编辑）",
                "# 每行: 用户名或账号=游戏内UID，# 开头为注释",
            ]
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            k, v = k.strip(), re.sub(r"\D", "", v)
            if not k or not v:
                continue
            if k == key or _match(k, target) or _match(target, k):
                if v == got:
                    logger.info(f"[切号] UID 已记录: {_mask_text(k)}={got}")
                else:
                    logger.error(f"[切号] UID 记录冲突: 现有 {_mask_text(k)}={v}，实际 {got}，不覆盖，请人工核对")
                return
        lines.append(f"{key}={got}")
        tmp = p.with_name(p.name + ".tmp")  # 先写临时文件再原子替换，防进程被杀截断
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(p)
        logger.info(f"[切号] UID 已记录: {_mask_text(key)}={got}")
    except Exception as e:
        logger.warning(f"[切号] 写入 zz_uid_map.txt 失败: {e}")
    finally:
        _FLOW_LOGGED_AT = 0.0  # 只记一次


def _at_login_dialog(self, boxes=None) -> bool:
    """当前是否已停在账号登录对话框（账号框+登录按钮同时在场）；
    已有 OCR 结果时可传入 boxes 复用，省一次全屏扫描"""
    acct = btn = False
    for b in (self.operator.ocr_boxes() if boxes is None else boxes or []):
        src = b.source or ""
        if _ACCT_PAT.search(src) or "邮箱" in src:
            acct = True
        if ("登录" in src or "进入游戏" in src) and "其他账号" not in src and "欢迎" not in src:
            btn = True
    return acct and btn


def _open_login_dialog(self, timeout: float = 25) -> bool:
    """欢迎页点右侧「登入」（mi 图标）打开账号登录对话框"""
    deadline = time.time() + timeout
    clicked = False
    while time.time() < deadline:
        boxes = self.operator.ocr_boxes() or []  # 一次扫描同时用于在位判断和找按钮
        if _at_login_dialog(self, boxes):
            return True
        box = next((b for b in boxes if "登入" in (b.source or "")), None)
        if box is not None:
            self.operator.click_box(box, after_sleep=2)
            clicked = True
        elif IMG is not None and MAIMG is not None and not clicked:
            try:  # OCR 失效时用 mi 图标模板兜底，只点一次
                self.operator.click_img(MAIMG.LOGOUT, after_sleep=2)
                clicked = True
            except Exception:
                pass
        self.operator.sleep(2)
    return _at_login_dialog(self)


def _safe_logout(self, timeout: float = 45) -> bool:
    """任意画面安全登出：主路线走电源图标模板（主界面和手机菜单里没有
    「登出」文本，OCR 找不到）；「返回登录页面」不触碰登录记录"""
    if _at_login_dialog(self):
        return True
    deadline = time.time() + timeout
    last_esc = 0.0
    while time.time() < deadline:
        boxes = self.operator.ocr_boxes() or []
        srcs = [b.source or "" for b in boxes]
        if _at_login_dialog(self, boxes):  # 复用本轮扫描结果
            return True
        if any("登录记录" in s for s in srcs):  # 保留/清除弹窗悬空，优先处理
            if not _confirm_logout_keep(self):
                return False
            continue
        if "登入" in srcs:  # 已回登录欢迎页
            return _open_login_dialog(self)
        if any(s == "登出" for s in srcs):  # 旧版界面的文本登出按钮
            box = next(b for b in boxes if (b.source or "") == "登出")
            self.operator.click_box(box, after_sleep=1)
            continue
        if IMG is not None and MAIMG is not None:  # 主路线：电源图标
            try:
                pbox = self.operator.wait_img(MAIMG.POWER, timeout=1)
            except Exception:
                pbox = None
            if pbox:
                self.operator.click_box(pbox, after_sleep=1)
                cbox = self.operator.wait_ocr_any(["确认"], interval=1, timeout=4)
                if cbox and cbox[1] is not None:
                    self.operator.click_box(cbox[1], after_sleep=2)
                elif IMG is not None:
                    try:
                        self.operator.click_img(IMG.ENSURE, after_sleep=2)
                    except Exception:
                        pass
                continue
        if time.time() - last_esc >= 4:  # 周期 ESC 剥多层残留画面
            self.operator.press_key("esc")
            last_esc = time.time()
        self.operator.sleep(2)
    logger.error("[切号] 登出失败，交由 AUTO-MAS 重试")
    return False


def _click_dialog_confirm(self, cancel) -> bool:
    """点登出弹窗确认键：与「取消」同行右侧的全等「退出」，否则 quit2 模板兜底
    （右上竖条菜单也有「退出」，全屏找会误点，必须几何定位）"""
    if cancel is not None:
        cy = cancel.top + cancel.height / 2
        cx = cancel.left + cancel.width / 2
        for b in self.operator.ocr_boxes() or []:
            if (b.source or "") != "退出":
                continue
            by = b.top + b.height / 2
            bx = b.left + b.width / 2
            if abs(by - cy) <= max(cancel.height, b.height) and bx > cx:
                self.operator.click_box(b, after_sleep=1)
                return True
    if IMG is not None:
        self.operator.click_img(IMG.QUIT2, after_sleep=1)
        return True
    return False


def _confirm_logout_keep(self) -> bool:
    """登出弹窗固定点「保留」方块 (0.363,0.530) + 「退出」(0.567,0.630)，
    OCR 验证弹窗消失，未消失几何定位兜底；坐标为比例值，任意分辨率通用"""
    boxes = []
    deadline = time.time() + 8
    while time.time() < deadline:  # 等弹窗渲染
        boxes = self.operator.ocr_boxes() or []
        if any("登录记录" in (b.source or "") for b in boxes):
            break
        self.operator.sleep(1)
    else:
        logger.info("[切号] 未检测到登出确认弹窗，视为已登出")
        return True
    has_keep = any("保留登录记录" in (b.source or "") for b in boxes)
    has_clear = any("清除登录记录" in (b.source or "") for b in boxes)
    if not has_keep and has_clear:
        logger.error("[切号] 弹窗无「保留」选项，取消登出保号")
        cancel = next((b for b in boxes if (b.source or "") == "取消"), None)
        if cancel is not None:
            self.operator.click_box(cancel, after_sleep=1)
        return False
    self.operator.click_point(0.363, 0.530, after_sleep=1)  # 「保留」单选方块（无文本，仅此一处用固定点）
    cancel = next((b for b in boxes if (b.source or "") == "取消"), None)
    if _click_dialog_confirm(self, cancel):  # 优先「取消」同行右侧的「退出」几何定位
        self.operator.sleep(2)
    else:
        self.operator.click_point(0.567, 0.630, after_sleep=3)  # 几何定位失效退回固定坐标
    for _ in range(3):  # 过渡期 OCR 可能有残影，多等多验
        self.operator.sleep(2)
        boxes = self.operator.ocr_boxes() or []
        if not any("登录记录" in (b.source or "") for b in boxes):
            return True
        logger.warning("[切号] 登出弹窗未关闭，兜底重试")
        cancel = next((b for b in boxes if (b.source or "") == "取消"), None)
        _click_dialog_confirm(self, cancel)
    logger.error("[切号] 登出确认弹窗多次未关闭，交由 AUTO-MAS 重试")
    return False


def _dismiss_agreement(self, tries: int = 3) -> None:
    """隐私协议弹窗兜底：点「同意」后复检最多 tries 轮；没弹窗只扫一次不拖时间"""
    for _ in range(tries):
        box = next((b for b in (self.operator.ocr_boxes() or [])
                    if (b.source or "").strip() in ("同意", "同意并继续")), None)
        if box is None:
            return
        self.operator.click_box(box, after_sleep=2)


def _quick_login(self) -> int:
    """快速登录页直点「进入游戏」；找不到按钮则报错"""
    btn = None
    for b in (self.operator.ocr_boxes() or []):
        src = b.source or ""
        # 「登录」全等匹配，防误点「登录其他账号」
        if ("进入游戏" in src or src == "登录") and "其他账号" not in src and "欢迎" not in src:
            btn = b
            break
    if btn is None:
        logger.error("[切号] 未找到「进入游戏」按钮，交由 AUTO-MAS 重试")
        return -1
    self.operator.click_box(btn, after_sleep=1)
    _dismiss_agreement(self)  # 隐私协议弹窗兜底
    return _wait_entered(self)


def _wait_login_page(self, timeout: float = 40) -> None:
    """轮询等登录界面稳定：账号框+登录按钮都在场才算；元素不齐才把
    12+/点击进入 当过渡页点掉（登录页左上角常驻 12+ 徽标不算过渡页）"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        boxes = self.operator.ocr_boxes() or []
        if any("登录记录" in (b.source or "") for b in boxes):
            self.operator.sleep(2)  # 登出弹窗悬空挡屏，等它消失
            continue
        acct = False
        btn = False
        for b in boxes:
            src = b.source or ""
            if _ACCT_PAT.search(src) or "邮箱" in src:
                acct = True
            if ("登录" in src or "进入游戏" in src) and "其他账号" not in src and "欢迎" not in src:
                btn = True
        if acct and btn:
            return
        for b in boxes:
            src = b.source or ""
            if src in ("12+", "CADPA") or "适龄" in src or "未成年人" in src:
                self.operator.click_box(b, after_sleep=2)
                break
            if "点击进入" in src:
                self.operator.click_box(b, after_sleep=2)
                break
        self.operator.sleep(2)
    raise RuntimeError("等待登录界面超时")


def _switch_by_history(self, hint: str) -> bool:
    """点账号框触发历史账号下拉 → 选目标号 → 确认登录（不进入游戏）"""
    _wait_login_page(self)
    boxes = self.operator.ocr_boxes()
    if boxes is None:
        raise RuntimeError("未检测到登录界面")
    acct = login = None
    for b in boxes:
        src = b.source or ""
        if ("登录" in src or "进入游戏" in src) and "其他账号" not in src and "退出" not in src:
            login = b
        if acct is None and (_ACCT_PAT.search(src) or "邮箱" in src):
            acct = b
    if acct is None or login is None:
        raise RuntimeError("未找到账号信息框或登录按钮")

    self.operator.click_box(acct, after_sleep=1)  # 触发历史账号下拉
    target = None
    seen: list[str] = []
    deadline = time.time() + 8
    while time.time() < deadline:
        for b in (self.operator.ocr_boxes() or []):
            txt = b.source or ""
            if re.search(r"(秒|分钟|小时|天|周|月|年)前|刚刚|昨天|今天", txt):
                continue  # 条目的时间戳行，点了会选中错误账号
            if txt not in seen:
                seen.append(txt)
            if _match(hint, txt):
                target = b
                break
        if target is not None:
            break
        self.operator.sleep(0.5)
    if target is None:
        logger.error(f"[切号] 下拉中未找到账号「{_mask_text(hint)}」，候选: {[_mask_text(s) for s in seen[:10]]}")
        return False
    logger.info(f"[切号] 选中历史账号: {_mask_text(target.source or '')}")
    self.operator.click_box(target, after_sleep=2)  # 客户端自动回填记住的密码

    confirm = None  # 下拉可能遮挡原坐标，重新定位确认按钮
    for b in (self.operator.ocr_boxes() or []):
        src = b.source or ""
        if ("登录" in src or "进入游戏" in src) and "其他账号" not in src and "退出" not in src:
            confirm = b
            break
    if confirm is not None:
        self.operator.click_box(confirm, after_sleep=1)
    _dismiss_agreement(self)  # 隐私协议弹窗兜底
    return True


def _ocr_shown_account(self) -> str:
    """识别登录页当前显示的脱敏账号"""
    for b in (self.operator.ocr_boxes() or []):
        src = b.source or ""
        if _ACCT_PAT.search(src):
            return src
    return ""


def _mas_switch_login(self, target: str) -> int:
    """花名册模式登录：核对/切换到目标账号后再进游戏"""
    state = self._detect_login_state()
    if state is None:
        logger.error("[切号] 未等到登录界面，交由 AUTO-MAS 重试")
        return -1
    if state == LoginStatus.NEW_VERSION_PAGE:
        logger.error("[切号] 游戏需要更新，交由 AUTO-MAS 重试")
        return -1
    if state == LoginStatus.LOGIN_PAGE:
        shown = _ocr_shown_account(self)
        if shown and _match(target, shown):
            logger.info(f"[切号] 记住账号 {shown} 与目标一致，直接登录")
            r = _quick_login(self)
            if r == 1:
                _mark_verified(self, target)
            return r
        logger.info(f"[切号] 记住账号({shown or '未识别'}) ≠ 目标，执行切号")
        if _switch_by_history(self, target):
            r = _wait_entered(self)
            if r == 1:
                _mark_verified(self, target)
            return r
        logger.error("[切号] 切号失败，交由 AUTO-MAS 重试")
        return -1
    # 已在游戏主界面：核对过且目标一致则沿用，否则登出重核
    if _check_verified(self, target):
        logger.info("[切号] 游戏内会话为已核对的目标账号，沿用")
        return int(state)
    logger.info("[切号] 游戏已登录，登出后切到目标账号")
    if _safe_logout(self) and _switch_by_history(self, target):
        r = _wait_entered(self)
        if r == 1:
            _mark_verified(self, target)
        return r
    logger.error("[切号] 登出/切号失败，沿用当前登录状态（错号风险）")
    return int(state)


if StartGameTask is not None and not getattr(StartGameTask, "_zz_patched", False):
    _orig_fill = _orig_login = _orig_laeg = None
    try:
        _orig_fill = StartGameTask._fill_credentials
    except AttributeError:
        logger.warning("[切号] 原版 _fill_credentials 不存在，插件未启用")
    try:
        _orig_login = StartGameTask.login
    except AttributeError:
        _orig_login = None
    try:
        _orig_laeg = StartGameTask.login_and_enter_game
    except AttributeError:
        _orig_laeg = None
    if _orig_fill is None and _orig_login is None:
        logger.warning("[切号] 无可用挂载点，插件未启用")

    def _fill_credentials(self):
        """账密填全走原逻辑；未填全且有提示词时走历史账号切号"""
        global _FLOW_LOGGED_AT
        try:
            user = encryption.decryptor(self.config.StartGame.EncryptedUsername)
            passwd = encryption.decryptor(self.config.StartGame.EncryptedPassword)
        except Exception as e:
            logger.warning(f"[切号] 读取登录配置失败，交还原版逻辑: {e}")
            return _orig_fill(self)
        if user == "" or passwd == "":
            hint = _load_hint()
            if hint:
                try:
                    logger.info(f"[切号] 账密未填全，改用历史账号切号（提示词: {_mask_text(hint)}）")
                    _FLOW_LOGGED_AT = time.time()
                    return _switch_by_history(self, hint)
                except Exception as e:
                    logger.error(f"[切号] 切号流程异常，放弃自动登录: {e!r}")
                    return False
            logger.error("[切号] 登录账密未设置且 account_hint.txt 为空")
            return False
        return _orig_fill(self)

    def _mas_login(self) -> int:
        """花名册模式优先；非 MAS 拉起或密码登录模式走原版"""
        if _orig_login is None:
            return -1
        if LoginStatus is None:
            return _orig_login(self)
        try:
            target = _mas_target()
        except Exception as e:
            logger.warning(f"[切号] 解析 MAS 目标失败: {e!r}")
            target = ""
        if not target or self.config.StartGame.isAutoLogin:
            return _orig_login(self)
        try:
            return _mas_switch_login(self, target)
        except Exception as e:
            logger.error(f"[切号] 花名册切号流程异常: {e!r}，交由 AUTO-MAS 重试")
            return -1

    def _laeg_with_uid(self, _retry_count: int = 0):
        """login_and_enter_game 包装：进游戏后做 UID 校验与自动记录；
        沿用会话的 UID 未见或属他人 → 登出重切，最多 2 次"""
        global _FLOW_LOGGED_AT
        try:
            r = _orig_laeg(self, _retry_count)
            if r is not True:
                return r
            try:
                target = _mas_target() or _load_hint()
                if not target:
                    return r
                now = time.time()
                fresh = 0 < _FLOW_LOGGED_AT <= now and now - _FLOW_LOGGED_AT <= _FLOW_WINDOW
                got = _read_game_uid(self, timeout=12)
                if not got and fresh:
                    got = _read_game_uid(self, timeout=15)  # 刚登录，画面可能还在加载
                if not got:
                    if fresh:  # 插件刚选的号，身份可信
                        logger.warning("[切号] 未能读取游戏内 UID，插件登录会话放行")
                        return r
                    logger.error("[切号] 沿用会话且读不到 UID，宁报错勿错号")
                    return False
                umap = _load_uid_map()  # 只读一次，target/owner 共用
                want = _target_uid(target, umap)
                owner = _uid_owner(got, umap)
                if want and got != want:
                    logger.error(f"[切号] UID 校验失败: 游戏内 {got} ≠ 目标 {want}")
                    return _uid_retry(self, target, _retry_count)
                if not want:
                    trusted = owner == _MAS_USER or _match(owner, target) or _match(target, owner)
                    if owner and not trusted:
                        logger.error(f"[切号] UID {got} 属于「{_mask_text(owner)}」，非目标账号，登出重切")
                        return _uid_retry(self, target, _retry_count)
                    if not owner and not fresh:
                        logger.warning(f"[切号] UID {got} 未见过且非本次登录会话，登出重切")
                        return _uid_retry(self, target, _retry_count)
                logger.info(f"[切号] UID 校验通过: {got}" + (f"（目标 {want}）" if want else ""))
                if fresh:
                    _record_uid(self, target, got)
                return r
            except Exception as e:
                logger.error(f"[切号] UID 校验流程异常: {e!r}")
                return False
        finally:
            _FLOW_LOGGED_AT = 0.0  # 离开流程即清，防异常中断后残留误判下一会话

    def _uid_retry(self, target: str, _retry_count: int):
        """UID 校验失败：清标记 → 安全登出 → 重新走原版流程（最多 2 次）"""
        global _FLOW_LOGGED_AT
        _clear_verified(self)
        _FLOW_LOGGED_AT = 0.0
        if _retry_count >= 2:
            logger.error("[切号] 重切 2 次 UID 仍不匹配，请核对 zz_uid_map.txt")
            return False
        if not _safe_logout(self):
            return False
        logger.info("[切号] 已退回登录界面，重新切号登录")
        try:
            return _laeg_with_uid(self, _retry_count + 1)
        except Exception as e:
            logger.error(f"[切号] 重切流程异常: {e!r}，交由 AUTO-MAS 重试")
            return False

    # CLI 默认 --log-level TRACE，OCR 坐标/模板探测刷屏；降为 INFO（放 zz_debug.txt 可恢复）
    if not (Path.cwd() / "zz_debug.txt").exists():
        try:
            from SRACore.util.logger import setup_logger
            setup_logger(level="INFO")
        except Exception:
            pass
    if _orig_fill is not None:
        StartGameTask._fill_credentials = _fill_credentials
    if _orig_login is not None:
        StartGameTask.login = _mas_login
    if _orig_laeg is not None:
        StartGameTask.login_and_enter_game = _laeg_with_uid
    # 辅助方法挂到类上（测试脚本可能直接调用）
    StartGameTask._switch_by_history = _switch_by_history
    StartGameTask._load_account_hint = staticmethod(_load_hint)
    StartGameTask._norm_acct = staticmethod(_norm)
    StartGameTask._acct_match = staticmethod(_match)
    StartGameTask._mas_target = staticmethod(_mas_target)
    StartGameTask._mas_context = staticmethod(_mas_context)
    StartGameTask._decrypt_mas_id = staticmethod(_decrypt_mas_id)
    StartGameTask._ocr_shown_account = _ocr_shown_account
    StartGameTask._quick_login = _quick_login
    StartGameTask._wait_login_page = _wait_login_page
    StartGameTask._mark_verified = _mark_verified
    StartGameTask._check_verified = _check_verified
    StartGameTask._safe_logout = _safe_logout
    StartGameTask._at_login_dialog = _at_login_dialog
    StartGameTask._open_login_dialog = _open_login_dialog
    StartGameTask._confirm_logout_keep = _confirm_logout_keep
    StartGameTask._click_dialog_confirm = _click_dialog_confirm
    StartGameTask._read_game_uid = _read_game_uid
    StartGameTask._uid_owner = staticmethod(_uid_owner)
    StartGameTask._target_uid = staticmethod(_target_uid)
    StartGameTask._load_uid_map = staticmethod(_load_uid_map)
    StartGameTask._mask_acct = staticmethod(_mask_acct)
    StartGameTask._mask_text = staticmethod(_mask_text)
    StartGameTask._zz_patched = True  # 幂等标记：防热重载/二次 import 后 _orig_login 捕获到已打补丁的方法
    logger.info("[切号] 插件已启用 v2.6.2")
elif StartGameTask is not None:
    logger.warning("[切号] 插件已挂载过，跳过重复加载")
