import smtplib
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Callable

from plyer import notification  # type: ignore

from SRACore.util import encryption
from SRACore.util.data_persister import load_settings
from SRACore.util.image_util import compress_image_bytes


# ===================== 核心分发 =====================

_cached_game_screenshot_bytes: bytes | None = None
_cached_game_screenshot_owner_id: int | None = None
_active_notification_screenshot_bytes: bytes | None = None
_notification_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notify_batch")


def try_send_notification(title: str, message: str, result: str = "success", operator: Any | None = None):
    setting = load_settings("notifications")
    if not setting.get("enabled", False):
        return
    screenshot_bytes = None
    if should_capture_notification_screenshot(setting):
        screenshot_bytes = _capture_game_window_bytes(operator)
        if not screenshot_bytes:
            screenshot_bytes = _get_cached_game_screenshot_bytes(operator)
    data = _build_notification_data(title, message, result)
    clear_cached_game_screenshot()
    _notification_executor.submit(_dispatch_notification_batch, title, message, data, dict(setting), screenshot_bytes)


# ===================== 工具函数 =====================
def _build_notification_data(title: str, message: str, result: str = "success") -> dict:
    from datetime import datetime
    return {
        "title": title,
        "message": message,
        "result": result,
        "event": title,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _fmt_msg(data: dict) -> str:
    """把通知数据包格式化为多行文本（用 \\n 拼接，绝不依赖字面换行）"""
    lines = [
        "[SRA 通知]",
        "事件: " + data.get("event", ""),
        "结果: " + data.get("result", ""),
        "时间: " + data.get("timestamp", ""),
        "消息: " + data.get("message", ""),
    ]
    return "\n".join(lines)


def _http_post_json(url: str, payload: dict, proxy_url: str | None = None) -> tuple[int, str]:
    """用标准库发 JSON POST，返回 (status_code, body_text)"""
    import json
    import urllib.error
    import urllib.request
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "StarRailAssistant/1.0",
    }
    if proxy_url:
        handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with opener.open(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _build_notification_jobs(
        title: str,
        message: str,
        data: dict,
        setting: dict[str, Any]) -> list[tuple[str, Callable[..., Any], tuple[Any, ...]]]:
    jobs: list[tuple[str, Callable[..., Any], tuple[Any, ...]]] = []
    if setting.get("system.enabled", False):
        jobs.append(("系统", send_windows_notification, (title, message)))
    if setting.get("email.enabled", False):
        jobs.append(("邮件", send_mail_notification, (data, setting)))
    if setting.get("webhook.enabled", False):
        jobs.append(("Webhook", send_webhook_notification, (data, setting)))
    if setting.get("telegram.enabled", False):
        jobs.append(("Telegram", send_telegram_notification, (data, setting)))
    if setting.get("serverChan.enabled", False):
        jobs.append(("ServerChan", send_serverchan_notification, (data, setting)))
    if setting.get("oneBot.enabled", False):
        jobs.append(("OneBot", send_onebot_notification, (data, setting)))
    if setting.get("bark.enabled", False):
        jobs.append(("Bark", send_bark_notification, (data, setting)))
    if setting.get("feishu.enabled", False):
        jobs.append(("飞书", send_feishu_notification, (data, setting)))
    if setting.get("weCom.enabled", False):
        jobs.append(("企业微信", send_wecom_notification, (data, setting)))
    if setting.get("dingTalk.enabled", False):
        jobs.append(("钉钉", send_dingtalk_notification, (data, setting)))
    if setting.get("discord.enabled", False):
        jobs.append(("Discord", send_discord_notification, (data, setting)))
    if setting.get("xxtui.enabled", False):
        jobs.append(("xxtui", send_xxtui_notification, (data, setting)))
    return jobs


def _dispatch_notification_batch(
        title: str,
        message: str,
        data: dict,
        setting: dict[str, Any],
        screenshot_bytes: bytes | None) -> None:
    global _active_notification_screenshot_bytes

    _active_notification_screenshot_bytes = screenshot_bytes
    try:
        _run_notification_jobs(_build_notification_jobs(title, message, data, setting))
    finally:
        _active_notification_screenshot_bytes = None


def _run_notification_job(channel_name: str, func: Callable[..., Any], args: tuple[Any, ...]) -> None:
    from SRACore.util.logger import logger

    try:
        func(*args)
    except Exception as e:
        logger.warning(channel_name + " 通知发送失败: " + str(e))


def _run_notification_jobs(jobs: list[tuple[str, Callable[..., Any], tuple[Any, ...]]]) -> None:
    if not jobs:
        return

    with ThreadPoolExecutor(max_workers=len(jobs), thread_name_prefix="notify") as executor:
        futures = [executor.submit(_run_notification_job, channel_name, func, args) for channel_name, func, args in jobs]
        for future in futures:
            future.result()


def _load_json_body(body: str) -> dict[str, Any] | None:
    import json

    if not body:
        return None
    try:
        data = json.loads(body)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _check_wecom_response(status: int, body: str) -> tuple[bool, str]:
    if not (200 <= status < 300):
        return False, "状态码: " + str(status)

    data = _load_json_body(body)
    if data is None:
        return False, "响应解析失败: " + body[:200]

    errcode = data.get("errcode")
    errmsg = str(data.get("errmsg", ""))
    if errcode == 0:
        return True, errmsg or "ok"
    return False, "errcode=" + str(errcode) + "; errmsg=" + errmsg


def should_capture_notification_screenshot(setting: dict[str, Any] | None = None) -> bool:
    config = setting or load_settings()
    return any([
        config.get("telegram.enabled", False) and config.get("telegram.sendImage", False),
        config.get("oneBot.enabled", False) and config.get("oneBot.sendImage", False),
        config.get("weCom.enabled", False) and config.get("weCom.sendImage", False),
        config.get("discord.enabled", False) and config.get("discordSendImage", False),
    ])


def capture_game_screenshot(operator: Any | None = None) -> bytes | None:
    global _cached_game_screenshot_bytes, _cached_game_screenshot_owner_id
    img_bytes = _capture_game_window_bytes(operator)
    if img_bytes:
        _cached_game_screenshot_bytes = img_bytes
        _cached_game_screenshot_owner_id = id(operator) if operator is not None else None
    return img_bytes


def clear_cached_game_screenshot() -> None:
    global _cached_game_screenshot_bytes, _cached_game_screenshot_owner_id
    _cached_game_screenshot_bytes = None
    _cached_game_screenshot_owner_id = None


def _get_cached_game_screenshot_bytes(operator: Any | None = None) -> bytes | None:
    if _cached_game_screenshot_bytes is None:
        return None
    if operator is None:
        return _cached_game_screenshot_bytes
    if _cached_game_screenshot_owner_id == id(operator):
        return _cached_game_screenshot_bytes
    return None


def _capture_game_window_bytes(operator: Any | None = None) -> bytes | None:
    try:
        import io
        if operator is None:
            from SRACore.operators import Operator
            operator = Operator()
        screenshot = operator.screenshot()
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _take_screenshot_bytes() -> bytes | None:
    """优先返回缓存的游戏截图，否则尝试截取当前游戏窗口"""
    if _active_notification_screenshot_bytes:
        return _active_notification_screenshot_bytes
    cached = _get_cached_game_screenshot_bytes()
    if cached:
        return cached
    return capture_game_screenshot()


def _take_screenshot_base64() -> str | None:
    """返回通知截图的 base64 字符串；失败返回 None"""
    import base64
    raw = _take_screenshot_bytes()
    return base64.b64encode(raw).decode() if raw else None


def _get_test_image_bytes() -> bytes | None:
    """返回 SRA 图标 PNG bytes，用于测试通知（resources/SRAico.png）"""
    import os
    path = os.path.join("resources", "SRAico.png")
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


# ===================== Windows 系统通知 =====================

def send_windows_notification(title: str, message: str, timeout: int = 5):
    fn = getattr(notification, "notify", None)
    if callable(fn):
        fn(title=title, message=message, app_name="SRA", timeout=timeout)


# ===================== 邮件通知 =====================

def send_mail_notification(title: str | dict = "SRA", message: str | dict[str, Any] = "",
                           configure: dict[str, Any] | None = None):
    if isinstance(title, dict):
        data = title
        config: dict[str, Any] = message if isinstance(message, dict) and configure is None else (configure or {})
        mail_title = str(data.get("title", "SRA")).strip() or "SRA"
        mail_message = _fmt_msg(data)
    else:
        config = configure or {}
        mail_title = title
        mail_message = message if isinstance(message, str) else ""

    SMTP = config.get("SmtpServer", "")
    port = config.get("SmtpPort", 465)
    sender = config.get("EmailSender", "")
    auth_code = config.get("EmailAuthCode", "")
    password = encryption.win_decryptor(auth_code) if auth_code else ""
    receiver = config.get("EmailReceiver", "")
    send_mail(mail_title, "SRA通知", mail_message, SMTP, port, sender, password, receiver)


def send_mail(title: str = "SRA", subject: str = "SRA通知", message: str = "",
              SMTP: str = "", port: int = 465, sender: str = "",
              password: str = "", receiver: str = "") -> bool:
    if not SMTP or not sender or not password or not receiver:
        return False
    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["From"] = formataddr((title, sender))
        msg["To"] = formataddr(("User", receiver))
        msg["Subject"] = subject
        server = smtplib.SMTP_SSL(SMTP, port)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        return True
    except Exception:
        raise


def send_test_email() -> bool:
    try:
        settings = load_settings()
        if not settings.get("AllowEmail.enabled", False):
            print("邮件通知未启用")
            return False
        required = ["SmtpServer", "EmailSender", "EmailAuthCode", "EmailReceiver"]
        missing = [f for f in required if not settings.get(f)]
        if missing:
            print("邮件配置不完整，缺少: " + ", ".join(missing))
            return False
        body_lines = [
            "这是一条测试信息。",
            "",
            "如果您收到此邮件，说明邮件通知功能配置正确。",
            "",
            "配置信息：",
            "- SMTP服务器: " + str(settings.get("SmtpServer")),
            "- 端口: " + str(settings.get("SmtpPort", 465)),
            "- 发送邮箱: " + str(settings.get("EmailSender")),
            "- 接收邮箱: " + str(settings.get("EmailReceiver")),
            "",
            "感谢您使用 StarRailAssistant！",
        ]
        send_mail_notification("SRA 测试邮件", "\n".join(body_lines), settings)
        print("测试邮件发送成功")
        return True
    except Exception as e:
        print("测试邮件发送失败: " + str(e))
        return False


# ===================== Webhook 通知 =====================

def send_webhook_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    from SRACore.util.logger import logger
    config = configure or {}
    endpoint = config.get("webhook.url", "").strip()
    if not endpoint:
        logger.warning("Webhook 通知发送失败: 未配置 WebhookEndpoint")
        return False
    try:
        status, body = _http_post_json(endpoint, data)
        if 200 <= status < 300:
            logger.debug("Webhook 通知发送成功")
            return True
        logger.warning("Webhook 通知发送失败，状态码: " + str(status))
        return False
    except Exception as e:
        logger.warning("Webhook 通知发送失败: " + str(e))
        return False


# ===================== Telegram 通知 =====================

def send_telegram_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """
    支持字段：TelegramBotToken, TelegramChatId, TelegramProxyEnabled,
              TelegramProxyUrl, TelegramApiBaseUrl, TelegramSendImage
    """
    from SRACore.util.logger import logger
    config = configure or {}
    bot_token = config.get("telegram.botToken", "").strip()
    chat_id = config.get("telegram.chatId", "").strip()
    proxy_url = config.get("telegram.proxyUrl", "").strip()
    proxy_enabled = config.get("telegram.proxyEnabled", False)
    api_base = config.get("telegram.apiBaseUrl", "").strip()
    send_image = config.get("telegram.sendImage", False)

    if not bot_token:
        logger.warning("Telegram 通知发送失败: 未配置 TelegramBotToken")
        return False
    if not chat_id:
        logger.warning("Telegram 通知发送失败: 未配置 TelegramChatId")
        return False

    if not api_base:
        api_base = "https://api.telegram.org/bot"
    else:
        if not api_base.startswith(("http://", "https://")):
            api_base = "https://" + api_base
        if not api_base.endswith("/"):
            api_base += "/"
        if not api_base.endswith("/bot"):
            api_base += "bot"

    effective_proxy = proxy_url if proxy_enabled and proxy_url else None

    try:
        status, body = _http_post_json(
            api_base + bot_token + "/sendMessage",
            {"chat_id": chat_id, "text": _fmt_msg(data), "disable_web_page_preview": True},
            proxy_url=effective_proxy,
        )
        if not (200 <= status < 300):
            logger.warning("Telegram 通知发送失败，状态码: " + str(status))
            return False
        logger.debug("Telegram 通知发送成功")
    except Exception as e:
        logger.warning("Telegram 通知发送失败: " + str(e))
        return False

    if send_image:
        img = _take_screenshot_bytes()
        if img:
            _telegram_send_photo(api_base, bot_token, chat_id, img, effective_proxy, logger)
        else:
            logger.warning("Telegram 截图失败，跳过图片发送")
    return True


def _telegram_send_photo(api_base, bot_token, chat_id, img_bytes, proxy_url, logger):
    import urllib.request
    boundary = "SRABoundary"
    crlf = b"\r\n"
    body = (
        b"--" + boundary.encode() + crlf
        + b'Content-Disposition: form-data; name="chat_id"' + crlf + crlf
        + chat_id.encode() + crlf
        + b"--" + boundary.encode() + crlf
        + b'Content-Disposition: form-data; name="photo"; filename="screenshot.png"' + crlf
        + b"Content-Type: image/png" + crlf + crlf
        + img_bytes + crlf
        + b"--" + boundary.encode() + b"--" + crlf
    )
    if proxy_url:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(
        api_base + bot_token + "/sendPhoto",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary,
                 "User-Agent": "StarRailAssistant/1.0"},
        method="POST",
    )
    try:
        with opener.open(req, timeout=30) as resp:
            if resp.status < 300:
                logger.debug("Telegram 截图发送成功")
            else:
                logger.warning("Telegram 截图发送失败，状态码: " + str(resp.status))
    except Exception as e:
        logger.warning("Telegram 截图发送失败: " + str(e))


# ===================== ServerChan 通知 =====================

def send_serverchan_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    import re
    from SRACore.util.logger import logger
    config = configure or {}
    send_key = config.get("serverChan.sendKey", "").strip()
    if not send_key:
        logger.warning("ServerChan 通知发送失败: 未配置 ServerChanSendKey")
        return False
    if send_key.startswith("sctp"):
        m = re.match(r"sctp(\d+)t", send_key)
        if not m:
            logger.warning("ServerChan 通知发送失败: SendKey 格式错误")
            return False
        url = "https://" + m.group(1) + ".push.ft07.com/send/" + send_key + ".send"
    else:
        url = "https://sctapi.ftqq.com/" + send_key + ".send"
    payload = {"title": data.get("title", "SRA 通知"), "desp": _fmt_msg(data)}
    try:
        status, body = _http_post_json(url, payload)
        if 200 <= status < 300:
            logger.debug("ServerChan 通知发送成功")
            return True
        logger.warning("ServerChan 通知发送失败，状态码: " + str(status))
        return False
    except Exception as e:
        logger.warning("ServerChan 通知发送失败: " + str(e))
        return False


# ===================== OneBot 通知 =====================

def _onebot_send(url: str, payload: dict, token: str) -> bool:
    import json
    import urllib.error
    import urllib.request
    from SRACore.util.logger import logger
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "StarRailAssistant/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("OneBot 请求失败: " + str(e))
        return False
    if not (200 <= status < 300):
        logger.warning("OneBot 请求失败，状态码: " + str(status))
        return False
    try:
        import json as _j
        r = _j.loads(body)
        if r.get("status") == "ok":
            return True
        logger.warning("OneBot 响应异常: " + body[:200])
        return False
    except Exception:
        return True  # 非标准响应，2xx 视为成功


def send_onebot_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """
    支持字段：OneBotEndpoint, OneBotUserId, OneBotGroupId, OneBotToken, OneBotSendImage
    """
    from SRACore.util.logger import logger
    config = configure or {}
    endpoint = config.get("oneBot.url", "").strip().rstrip("/")
    user_id = config.get("oneBot.userId", "").strip()
    group_id = config.get("oneBot.groupId", "").strip()
    token = config.get("oneBot.token", "").strip()
    send_image = config.get("oneBot.sendImage", False)

    if not endpoint:
        logger.warning("OneBot 通知发送失败: 未配置 OneBotEndpoint")
        return False
    if not user_id and not group_id:
        logger.warning("OneBot 通知发送失败: UserId 和 GroupId 至少填一个")
        return False

    url = endpoint if endpoint.endswith("/send_msg") else endpoint + "/send_msg"
    msg_seg = [{"type": "text", "data": {"text": _fmt_msg(data)}}]
    success = True
    if user_id:
        ok = _onebot_send(url, {"message_type": "private", "user_id": user_id, "message": msg_seg}, token)
        if not ok:
            success = False
    if group_id:
        ok = _onebot_send(url, {"message_type": "group", "group_id": group_id, "message": msg_seg}, token)
        if not ok:
            success = False

    if send_image:
        img_b64 = _take_screenshot_base64()
        if img_b64:
            img_seg = [{"type": "image", "data": {"file": "base64://" + img_b64}}]
            if user_id:
                _onebot_send(url, {"message_type": "private", "user_id": user_id, "message": img_seg}, token)
            if group_id:
                _onebot_send(url, {"message_type": "group", "group_id": group_id, "message": img_seg}, token)
            logger.debug("OneBot 截图发送完成")
        else:
            logger.warning("OneBot 截图失败，跳过图片发送")
    return success


# ===================== Bark 通知 =====================

def send_bark_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """
    支持字段：BarkDeviceKey（逗号分隔多设备）, BarkServerUrl,
              BarkLevel, BarkSound, BarkGroup, BarkIcon, BarkCiphertext
    """
    from SRACore.util.logger import logger
    config = configure or {}
    device_key_raw = config.get("bark.deviceKey", "").strip()
    server_url = config.get("bark.serverUrl", "https://api.day.app").strip().rstrip("/")
    if not device_key_raw:
        logger.warning("Bark 通知发送失败: 未配置 BarkDeviceKey")
        return False

    payload: dict = {
        "title": "SRA 通知",
        "body": _fmt_msg(data),
        "group": config.get("bark.group", "StarRailAssistant").strip() or "StarRailAssistant",
    }
    level = config.get("bark.level", "").strip()
    if level in ("active", "timeSensitive", "passive"):
        payload["level"] = level
    sound = config.get("bark.sound", "").strip()
    if sound:
        payload["sound"] = sound
    icon = config.get("bark.icon", "").strip()
    if icon:
        payload["icon"] = icon
    ciphertext = config.get("bark.ciphertext", "").strip()
    if ciphertext:
        payload["ciphertext"] = ciphertext

    success = True
    for dk in [k.strip() for k in device_key_raw.split(",") if k.strip()]:
        payload["device_key"] = dk
        try:
            status, body = _http_post_json(server_url + "/" + dk, payload)
            if 200 <= status < 300:
                logger.debug("Bark 通知发送成功: " + dk[:8] + "...")
            else:
                logger.warning("Bark 通知发送失败，状态码: " + str(status))
                success = False
        except Exception as e:
            logger.warning("Bark 通知发送失败: " + str(e))
            success = False
    return success


# ===================== 飞书通知 =====================

def send_feishu_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """
    方式一（Webhook）：FeishuWebhookUrl
    方式二（应用 API）：FeishuAppId, FeishuAppSecret, FeishuReceiveId, FeishuReceiveIdType
    """
    from SRACore.util.logger import logger
    config = configure or {}
    app_id = config.get("feishu.appId", "").strip()
    app_secret = config.get("feishu.appSecret", "").strip()
    webhook_url = config.get("feishu.webhookUrl", "").strip()
    msg = _fmt_msg(data)

    # 方式二：应用 API
    if app_id and app_secret:
        receive_id = config.get("feishu.receiveId", "").strip()
        id_type = config.get("feishu.receiveIdType", "open_id").strip() or "open_id"
        if not receive_id:
            logger.warning("飞书通知发送失败: 未配置 FeishuReceiveId")
            return False
        try:
            import json
            import urllib.request
            # 获取 tenant_access_token
            token_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
            req = urllib.request.Request(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                data=token_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_resp = json.loads(resp.read())
            access_token = token_resp.get("tenant_access_token", "")
            if not access_token:
                logger.warning("飞书通知发送失败: 获取 token 失败")
                return False
            # 发送消息
            payload = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": msg}),
            }
            send_req = urllib.request.Request(
                "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=" + id_type,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + access_token,
                         "User-Agent": "StarRailAssistant/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(send_req, timeout=10) as resp2:
                status = resp2.status
            if 200 <= status < 300:
                logger.debug("飞书通知发送成功（应用 API）")
                return True
            logger.warning("飞书通知发送失败，状态码: " + str(status))
            return False
        except Exception as e:
            logger.warning("飞书通知发送失败: " + str(e))
            return False

    # 方式一：Webhook
    if not webhook_url:
        logger.warning("飞书通知发送失败: 未配置 FeishuWebhookUrl 或 AppId/AppSecret")
        return False
    try:
        status, body = _http_post_json(webhook_url, {"msg_type": "text", "content": {"text": msg}})
        if 200 <= status < 300:
            logger.debug("飞书通知发送成功（Webhook）")
            return True
        logger.warning("飞书通知发送失败，状态码: " + str(status))
        return False
    except Exception as e:
        logger.warning("飞书通知发送失败: " + str(e))
        return False


# ===================== 企业微信通知 =====================

def send_wecom_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """支持字段：WeComWebhookUrl, WeComSendImage"""
    import hashlib
    from SRACore.util.logger import logger
    config = configure or {}
    webhook_url = config.get("weCom.webhookUrl", "").strip()
    send_image = config.get("weCom.sendImage", False)
    if not webhook_url:
        logger.warning("企业微信通知发送失败: 未配置 WeComWebhookUrl")
        return False

    payload = {"msgtype": "text", "text": {"content": _fmt_msg(data)}}
    try:
        status, body = _http_post_json(webhook_url, payload)
        ok, detail = _check_wecom_response(status, body)
        if not ok:
            logger.warning("企业微信通知发送失败: " + detail)
            return False
        logger.debug("企业微信通知发送成功")
    except Exception as e:
        logger.warning("企业微信通知发送失败: " + str(e))
        return False

    success = True
    if send_image:
        img = _take_screenshot_bytes()
        if img:
            import base64

            target_size = 2 * 1024 * 1024
            img_to_send = img
            quality = -1

            if len(img_to_send) > target_size:
                compressed, _, quality = compress_image_bytes(img_to_send, target_size)
                if not compressed:
                    logger.warning("企业微信截图压缩失败，跳过图片发送")
                    return False
                img_to_send = compressed

            img_b64 = base64.b64encode(img_to_send).decode()
            img_md5 = hashlib.md5(img_to_send).hexdigest()
            try:
                s2, body2 = _http_post_json(
                    webhook_url,
                    {"msgtype": "image", "image": {"base64": img_b64, "md5": img_md5}},
                )
                ok, detail = _check_wecom_response(s2, body2)
                if ok:
                    if quality >= 0:
                        logger.debug("企业微信截图发送成功（压缩质量 " + str(quality) + "）")
                    else:
                        logger.debug("企业微信截图发送成功")
                else:
                    logger.warning("企业微信截图发送失败: " + detail)
                    success = False
            except Exception as e:
                logger.warning("企业微信截图发送失败: " + str(e))
                success = False
        else:
            logger.warning("企业微信截图失败，跳过图片发送")
            success = False
    return success


# ===================== 钉钉通知 =====================

def send_dingtalk_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """支持字段：DingTalkWebhookUrl, DingTalkSecret（可选加签）"""
    import base64
    import hashlib
    import hmac
    import time
    import urllib.parse
    from SRACore.util.logger import logger
    config = configure or {}
    webhook_url = config.get("dingTalk.webhookUrl", "").strip()
    secret = config.get("dingTalk.secret", "").strip()
    if not webhook_url:
        logger.warning("钉钉通知发送失败: 未配置 DingTalkWebhookUrl")
        return False

    if secret:
        timestamp = str(round(time.time() * 1000))
        sign_str = timestamp + "\n" + secret
        hmac_code = hmac.new(secret.encode(), sign_str.encode(), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url = webhook_url + "&timestamp=" + timestamp + "&sign=" + sign

    md_lines = [
        "**[SRA 通知]**",
        "",
        "- 事件: " + data.get("event", ""),
        "- 结果: " + data.get("result", ""),
        "- 时间: " + data.get("timestamp", ""),
        "- 消息: " + data.get("message", ""),
    ]
    payload = {"msgtype": "markdown", "markdown": {"title": "SRA 通知", "text": "\n".join(md_lines)}}
    try:
        status, body = _http_post_json(webhook_url, payload)
        if 200 <= status < 300:
            logger.debug("钉钉通知发送成功")
            return True
        logger.warning("钉钉通知发送失败，状态码: " + str(status))
        return False
    except Exception as e:
        logger.warning("钉钉通知发送失败: " + str(e))
        return False


# ===================== Discord 通知 =====================

def send_discord_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """支持字段：DiscordWebhookUrl, DiscordSendImage"""
    import json
    import urllib.request
    from SRACore.util.logger import logger
    config = configure or {}
    webhook_url = config.get("discord.webhookUrl", "").strip()
    send_image = config.get("discord.sendImage", False)
    if not webhook_url:
        logger.warning("Discord 通知发送失败: 未配置 DiscordWebhookUrl")
        return False

    color = 0x00FF00 if data.get("result") == "success" else 0xFF0000
    payload = {
        "username": "StarRailAssistant",
        "embeds": [{
            "title": "SRA 通知",
            "color": color,
            "fields": [
                {"name": "事件", "value": data.get("event", ""), "inline": True},
                {"name": "结果", "value": data.get("result", ""), "inline": True},
                {"name": "时间", "value": data.get("timestamp", ""), "inline": True},
                {"name": "消息", "value": data.get("message", ""), "inline": False},
            ],
        }],
    }

    if send_image:
        img = _take_screenshot_bytes()
        if img:
            boundary = "SRABoundary"
            crlf = b"\r\n"
            json_bytes = json.dumps(payload, ensure_ascii=False).encode()
            body = (
                b"--" + boundary.encode() + crlf
                + b'Content-Disposition: form-data; name="payload_json"' + crlf
                + b"Content-Type: application/json" + crlf + crlf
                + json_bytes + crlf
                + b"--" + boundary.encode() + crlf
                + b'Content-Disposition: form-data; name="files[0]"; filename="screenshot.png"' + crlf
                + b"Content-Type: image/png" + crlf + crlf
                + img + crlf
                + b"--" + boundary.encode() + b"--" + crlf
            )
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "multipart/form-data; boundary=" + boundary,
                         "User-Agent": "StarRailAssistant/1.0"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status < 300:
                        logger.debug("Discord 通知（含截图）发送成功")
                        return True
                    logger.warning("Discord 通知发送失败，状态码: " + str(resp.status))
                    return False
            except Exception as e:
                logger.warning("Discord 通知发送失败: " + str(e))
                return False
        else:
            logger.warning("Discord 截图失败，降级为纯文本发送")

    try:
        status, body = _http_post_json(webhook_url, payload)
        if 200 <= status < 300:
            logger.debug("Discord 通知发送成功")
            return True
        logger.warning("Discord 通知发送失败，状态码: " + str(status))
        return False
    except Exception as e:
        logger.warning("Discord 通知发送失败: " + str(e))
        return False


# ===================== xxtui 通知 =====================

def send_xxtui_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    """支持字段：XxtuiApiKey, XxtuiSource（可选）, XxtuiChannel（可选）"""
    from SRACore.util.logger import logger
    config = configure or {}
    api_key = config.get("xxtui.apiKey", "").strip()
    if not api_key:
        logger.warning("xxtui 通知发送失败: 未配置 XxtuiApiKey")
        return False
    payload: dict = {"title": "SRA 通知", "content": _fmt_msg(data)}
    source = config.get("xxtui.source", "").strip()
    if source:
        payload["source"] = source
    channel = config.get("xxtui.channel", "").strip()
    if channel:
        payload["channel"] = channel
    try:
        status, body = _http_post_json("https://xxtui.com/send/" + api_key, payload)
        if 200 <= status < 300:
            logger.debug("xxtui 通知发送成功")
            return True
        logger.warning("xxtui 通知发送失败，状态码: " + str(status))
        return False
    except Exception as e:
        logger.warning("xxtui 通知发送失败: " + str(e))
        return False
