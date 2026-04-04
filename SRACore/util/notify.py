import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from plyer import notification  # type: ignore

from SRACore.util import encryption
from SRACore.util.data_persister import load_settings


# ===================== 核心分发 =====================

def try_send_notification(title: str, message: str, result: str = "success"):
    setting = load_settings()
    if not setting.get("AllowNotifications", False):
        return
    data = _build_notification_data(title, message, result)
    if setting.get("AllowSystemNotifications", False):
        send_windows_notification(title, message)
    if setting.get("AllowEmailNotifications", False):
        send_mail_notification(title, message, setting)
    if setting.get("AllowWebhookNotifications", False):
        send_webhook_notification(data, setting)
    if setting.get("AllowTelegramNotifications", False):
        send_telegram_notification(data, setting)
    if setting.get("AllowServerChanNotifications", False):
        send_serverchan_notification(data, setting)
    if setting.get("AllowOneBotNotifications", False):
        send_onebot_notification(data, setting)
    if setting.get("AllowBarkNotifications", False):
        send_bark_notification(data, setting)
    if setting.get("AllowFeishuNotifications", False):
        send_feishu_notification(data, setting)
    if setting.get("AllowWeComNotifications", False):
        send_wecom_notification(data, setting)
    if setting.get("AllowDingTalkNotifications", False):
        send_dingtalk_notification(data, setting)
    if setting.get("AllowDiscordNotifications", False):
        send_discord_notification(data, setting)
    if setting.get("AllowXxtuiNotifications", False):
        send_xxtui_notification(data, setting)


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


def _take_screenshot_bytes() -> bytes | None:
    """截取全屏，返回 PNG bytes；失败返回 None"""
    try:
        import io
        import pyscreeze
        buf = io.BytesIO()
        pyscreeze.screenshot().save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _take_screenshot_base64() -> str | None:
    """截取全屏，返回 base64 字符串；失败返回 None"""
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

def send_mail_notification(title: str = "SRA", message: str = "",
                           configure: dict[str, Any] | None = None):
    config: dict[str, Any] = configure or {}
    SMTP = config.get("SmtpServer", "")
    port = config.get("SmtpPort", 465)
    sender = config.get("EmailSender", "")
    auth_code = config.get("EmailAuthCode", "")
    password = encryption.win_decryptor(auth_code) if auth_code else ""
    receiver = config.get("EmailReceiver", "")
    send_mail(title, "SRA通知", message, SMTP, port, sender, password, receiver)


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
        if not settings.get("AllowEmailNotifications", False):
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
    endpoint = config.get("WebhookEndpoint", "").strip()
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
    bot_token = config.get("TelegramBotToken", "").strip()
    chat_id = config.get("TelegramChatId", "").strip()
    proxy_url = config.get("TelegramProxyUrl", "").strip()
    proxy_enabled = config.get("TelegramProxyEnabled", False)
    api_base = config.get("TelegramApiBaseUrl", "").strip()
    send_image = config.get("TelegramSendImage", False)

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
    send_key = config.get("ServerChanSendKey", "").strip()
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
    endpoint = config.get("OneBotEndpoint", "").strip().rstrip("/")
    user_id = config.get("OneBotUserId", "").strip()
    group_id = config.get("OneBotGroupId", "").strip()
    token = config.get("OneBotToken", "").strip()
    send_image = config.get("OneBotSendImage", False)

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
    device_key_raw = config.get("BarkDeviceKey", "").strip()
    server_url = config.get("BarkServerUrl", "https://api.day.app").strip().rstrip("/")
    if not device_key_raw:
        logger.warning("Bark 通知发送失败: 未配置 BarkDeviceKey")
        return False

    payload: dict = {
        "title": "SRA 通知",
        "body": _fmt_msg(data),
        "group": config.get("BarkGroup", "StarRailAssistant").strip() or "StarRailAssistant",
    }
    level = config.get("BarkLevel", "").strip()
    if level in ("active", "timeSensitive", "passive"):
        payload["level"] = level
    sound = config.get("BarkSound", "").strip()
    if sound:
        payload["sound"] = sound
    icon = config.get("BarkIcon", "").strip()
    if icon:
        payload["icon"] = icon
    ciphertext = config.get("BarkCiphertext", "").strip()
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
    app_id = config.get("FeishuAppId", "").strip()
    app_secret = config.get("FeishuAppSecret", "").strip()
    webhook_url = config.get("FeishuWebhookUrl", "").strip()
    msg = _fmt_msg(data)

    # 方式二：应用 API
    if app_id and app_secret:
        receive_id = config.get("FeishuReceiveId", "").strip()
        id_type = config.get("FeishuReceiveIdType", "open_id").strip() or "open_id"
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
    webhook_url = config.get("WeComWebhookUrl", "").strip()
    send_image = config.get("WeComSendImage", False)
    if not webhook_url:
        logger.warning("企业微信通知发送失败: 未配置 WeComWebhookUrl")
        return False

    md_lines = [
        "**[SRA 通知]**",
        "事件: " + data.get("event", ""),
        "结果: " + data.get("result", ""),
        "时间: " + data.get("timestamp", ""),
        "消息: " + data.get("message", ""),
    ]
    payload = {"msgtype": "markdown", "markdown": {"content": "\n".join(md_lines)}}
    try:
        status, body = _http_post_json(webhook_url, payload)
        if not (200 <= status < 300):
            logger.warning("企业微信通知发送失败，状态码: " + str(status))
            return False
        logger.debug("企业微信通知发送成功")
    except Exception as e:
        logger.warning("企业微信通知发送失败: " + str(e))
        return False

    if send_image:
        img = _take_screenshot_bytes()
        if img:
            import base64
            img_b64 = base64.b64encode(img).decode()
            img_md5 = hashlib.md5(img).hexdigest()
            try:
                s2, _ = _http_post_json(webhook_url,
                                        {"msgtype": "image", "image": {"base64": img_b64, "md5": img_md5}})
                if 200 <= s2 < 300:
                    logger.debug("企业微信截图发送成功")
                else:
                    logger.warning("企业微信截图发送失败，状态码: " + str(s2))
            except Exception as e:
                logger.warning("企业微信截图发送失败: " + str(e))
        else:
            logger.warning("企业微信截图失败，跳过图片发送")
    return True


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
    webhook_url = config.get("DingTalkWebhookUrl", "").strip()
    secret = config.get("DingTalkSecret", "").strip()
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
    webhook_url = config.get("DiscordWebhookUrl", "").strip()
    send_image = config.get("DiscordSendImage", False)
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
    api_key = config.get("XxtuiApiKey", "").strip()
    if not api_key:
        logger.warning("xxtui 通知发送失败: 未配置 XxtuiApiKey")
        return False
    payload: dict = {"title": "SRA 通知", "content": _fmt_msg(data)}
    source = config.get("XxtuiSource", "").strip()
    if source:
        payload["source"] = source
    channel = config.get("XxtuiChannel", "").strip()
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
