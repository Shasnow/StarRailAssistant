import json
import re
import smtplib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from plyer import notification # type: ignore

from SRACore.util import encryption
from SRACore.util.data_persister import load_settings
from SRACore.util.logger import logger


def try_send_notification(title: str, message: str, result: str = "success"):
    setting = load_settings()
    if not setting.get('AllowNotifications', False):
        return
    if setting.get('AllowSystemNotifications', False):
        send_windows_notification(title, message)
    if setting.get('AllowEmailNotifications', False):
        send_mail_notification(title, message, setting)

    if setting.get("AllowWebhookNotifications", False):
        data = _build_notification_data(title, message, result)
        send_webhook_notification(data, setting)

    if setting.get("AllowTelegramNotifications", False):
        data = _build_notification_data(title, message, result)
        send_telegram_notification(data, setting)

    if setting.get("AllowServerChanNotifications", False):
        data = _build_notification_data(title, message, result)
        send_serverchan_notification(data, setting)

    if setting.get("AllowOneBotNotifications", False):
        data = _build_notification_data(title, message, result)
        send_onebot_notification(data, setting)


def send_windows_notification(title: str, message: str, timeout: int = 5):
    """
    发送 Windows 系统通知
    :param title: 通知标题
    :param message: 通知内容
    :param timeout: 通知显示时长（秒）
    """

    # 发送通知
    notify_func = getattr(notification, "notify", None)
    if callable(notify_func):
        notify_func(title=title, message=message, app_name="SRA", timeout=timeout)


def send_mail_notification(title: str = "SRA", message: str = "", configure: dict[str, Any] | None = None):
    """发送邮件通知"""
    config: dict[str, Any] = configure or {}
    SMTP = config.get("SmtpServer", "")
    port = config.get("SmtpPort", 465)
    sender = config.get("EmailSender", "")
    auth_code = config.get("EmailAuthCode", "")
    password = encryption.win_decryptor(auth_code) if auth_code else ""
    receiver = config.get("EmailReceiver", "")
    send_mail(title, "SRA通知", message, SMTP, port, sender, password, receiver)


def send_mail(
        title: str = "SRA",
        subject: str = "SRA通知",
        message: str = "",
        SMTP: str = "",
        port: int = 465,
        sender: str = "",
        password: str = "",
        receiver: str = "",
) -> bool:
    """发送邮件"""
    if SMTP == "" or sender == "" or password == "" or receiver == "":
        return False
    try:
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['From'] = formataddr((title, sender))
        msg['To'] = formataddr(("User", receiver))
        msg['Subject'] = subject

        server = smtplib.SMTP_SSL(SMTP, port)
        server.login(sender, password)
        server.sendmail(sender, [receiver, ], msg.as_string())
        server.quit()
        return True
    except Exception:
        raise


def send_test_email() -> bool:
    """
    发送测试邮件
    :return: 是否发送成功
    """

    try:
        settings = load_settings()

        # 检查邮件通知是否启用
        if not settings.get('AllowEmailNotifications', False):
            print("邮件通知未启用")
            return False

        # 检查必要的配置
        required_fields = ['SmtpServer', 'EmailSender', 'EmailAuthCode', 'EmailReceiver']
        missing_fields = [field for field in required_fields if not settings.get(field)]

        if missing_fields:
            print(f"邮件配置不完整，缺少: {', '.join(missing_fields)}")
            return False

        # 发送测试邮件
        test_message = f"""这是一条测试信息。

如果您收到此邮件，说明邮件通知功能配置正确。

配置信息：
- SMTP服务器: {settings.get('SmtpServer')}
- 端口: {settings.get('SmtpPort', 465)}
- 发送邮箱: {settings.get('EmailSender')}
- 接收邮箱: {settings.get('EmailReceiver')}

感谢您使用 StarRailAssistant！
"""

        send_mail_notification('SRA 测试邮件', test_message, settings)
        print("测试邮件发送成功")
        return True

    except Exception as e:
        print(f"测试邮件发送失败: {e}")
        return False


# =================== 通知数据构造 ===================

def _build_notification_data(title: str, message: str, result: str = "success") -> dict:
    return {
        "event": title,
        "result": result,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
    }


def _http_post_json(url: str, payload: dict, timeout: int = 10,
                    proxy_url: str | None = None) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "StarRailAssistant/1.0"},
        method="POST",
    )
    if proxy_url:
        handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        opener = urllib.request.build_opener(handler)
    else:
        opener = urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _http_post_form(url: str, payload: dict, timeout: int = 10) -> tuple[int, str]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "StarRailAssistant/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


# =================== Webhook 通知 ===================

def send_webhook_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    config = configure or {}
    endpoint = config.get("WebhookEndpoint", "").strip()
    if not endpoint:
        logger.warning("Webhook 通知发送失败: 未配置 WebhookEndpoint")
        return False
    try:
        status, body = _http_post_json(endpoint, data)
        if 200 <= status < 300:
            logger.debug(f"Webhook 通知发送成功: {endpoint}")
            return True
        else:
            logger.warning(f"Webhook 通知发送失败，状态码: {status}，响应: {body[:200]}")
            return False
    except Exception as e:
        logger.warning(f"Webhook 通知发送失败: {e}")
        return False


# =================== Telegram 通知 ===================

def send_telegram_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    config = configure or {}
    bot_token = config.get("TelegramBotToken", "").strip()
    chat_id = config.get("TelegramChatId", "").strip()
    proxy_url = config.get("TelegramProxyUrl", "").strip()
    proxy_enabled = config.get("TelegramProxyEnabled", False)
    api_base = config.get("TelegramApiBaseUrl", "").strip()
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
    endpoint = f"{api_base}{bot_token}/sendMessage"
    message = (
        f"[SRA 通知]\n"
        f"事件: {data.get('event', '')}\n"
        f"结果: {data.get('result', '')}\n"
        f"时间: {data.get('timestamp', '')}\n"
        f"消息: {data.get('message', '')}"
    )
    effective_proxy = proxy_url if proxy_enabled and proxy_url else None
    try:
        status, body = _http_post_json(
            endpoint,
            {"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            proxy_url=effective_proxy,
        )
        if 200 <= status < 300:
            logger.debug(f"Telegram 通知发送成功: chat_id={chat_id}")
            return True
        else:
            logger.warning(f"Telegram 通知发送失败，状态码: {status}，响应: {body[:200]}")
            return False
    except Exception as e:
        logger.warning(f"Telegram 通知发送失败: {e}")
        return False


# =================== ServerChan 通知 ===================

def send_serverchan_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    config = configure or {}
    send_key = config.get("ServerChanSendKey", "").strip()
    if not send_key:
        logger.warning("ServerChan 通知发送失败: 未配置 ServerChanSendKey")
        return False
    if send_key.startswith("sctp"):
        match = re.match(r"^sctp(\d+)t", send_key)
        if not match:
            logger.warning("ServerChan 通知发送失败: SendKey 格式无效")
            return False
        num = match.group(1)
        api_url = f"https://{num}.push.ft07.com/send/{send_key}.send"
    else:
        api_url = f"https://sctapi.ftqq.com/{send_key}.send"
    title = "SRA 通知"
    desp = (
        f"**时间**: {data.get('timestamp', '')}\n\n"
        f"**事件**: {data.get('event', '')}\n\n"
        f"**结果**: {data.get('result', '')}\n\n"
        f"**消息**: {data.get('message', '')}"
    )
    try:
        status, body = _http_post_form(api_url, {"title": title, "desp": desp})
        if 200 <= status < 300:
            logger.debug("ServerChan 通知发送成功")
            return True
        else:
            logger.warning(f"ServerChan 通知发送失败，状态码: {status}，响应: {body[:200]}")
            return False
    except Exception as e:
        logger.warning(f"ServerChan 通知发送失败: {e}")
        return False


# =================== OneBot 通知 ===================

def send_onebot_notification(data: dict, configure: dict[str, Any] | None = None) -> bool:
    config = configure or {}
    endpoint = config.get("OneBotEndpoint", "").strip().rstrip("/")
    user_id = config.get("OneBotUserId", "").strip()
    group_id = config.get("OneBotGroupId", "").strip()
    token = config.get("OneBotToken", "").strip()
    if not endpoint:
        logger.warning("OneBot 通知发送失败: 未配置 OneBotEndpoint")
        return False
    if not user_id and not group_id:
        logger.warning("OneBot 通知发送失败: OneBotUserId 和 OneBotGroupId 至少需要填写一个")
        return False
    url = endpoint if endpoint.endswith("/send_msg") else endpoint + "/send_msg"
    message_text = (
        f"[SRA 通知]\n"
        f"事件: {data.get('event', '')}\n"
        f"结果: {data.get('result', '')}\n"
        f"时间: {data.get('timestamp', '')}\n"
        f"消息: {data.get('message', '')}"
    )
    message_content = [{"type": "text", "data": {"text": message_text}}]
    success = True
    if user_id:
        ok = _onebot_send(url, {"message_type": "private", "user_id": user_id, "message": message_content}, token)
        if not ok:
            success = False
    if group_id:
        ok = _onebot_send(url, {"message_type": "group", "group_id": group_id, "message": message_content}, token)
        if not ok:
            success = False
    return success


def _onebot_send(url: str, payload: dict, token: str) -> bool:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "StarRailAssistant/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"OneBot 通知发送失败: {e}")
        return False
    if not (200 <= status < 300):
        logger.warning(f"OneBot 通知发送失败，状态码: {status}，响应: {body[:200]}")
        return False
    try:
        resp_json = json.loads(body)
        if resp_json.get("status") == "ok":
            logger.debug(f"OneBot 通知发送成功: {url}")
            return True
        else:
            logger.warning(f"OneBot 通知发送失败，响应: {body[:200]}")
            return False
    except Exception:
        logger.debug(f"OneBot 通知发送成功（非标准响应）: {url}")
        return True
