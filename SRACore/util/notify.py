import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from plyer import notification # type: ignore

from SRACore.util import encryption
from SRACore.util.data_persister import load_settings


def try_send_notification(title: str, message: str):
    setting = load_settings()
    if not setting.get('AllowNotifications', False):
        return
    if setting.get('AllowSystemNotifications', False):
        send_windows_notification(title, message)
    if setting.get('AllowEmailNotifications', False):
        send_mail_notification(title, message, setting)


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
