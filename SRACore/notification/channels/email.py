from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from SRACore.notification.channels.base import NotificationChannel
from SRACore.notification.models import NotificationContext, format_notification_message
from SRACore.util.logger import logger
from SRACore.util import encryption


class EmailChannel(NotificationChannel):
    name = "邮件"
    enabled_attr = "isEmailEnabled"

    def send(self, context: NotificationContext) -> bool:
        config = context.settings
        password = encryption.decryptor(config.EncryptedSmtpAuthCode) if config.EncryptedSmtpAuthCode else ""
        return send_mail(
            title=str(context.payload.get("title", "SRA")).strip() or "SRA",
            subject="SRA通知",
            message=format_notification_message(context.payload),
            smtp_server=config.smtpServer,
            port=config.smtpPort,
            sender=config.smtpSender,
            password=password,
            receiver=config.smtpReceiver,
        )


def send_mail(
    title: str,
    subject: str,
    message: str,
    smtp_server: str,
    port: int,
    sender: str,
    password: str,
    receiver: str,
) -> bool:
    if not smtp_server or not sender or not password or not receiver:
        logger.warning("邮件通知发送失败：SMTP 配置不完整，请检查服务器、端口、发件人、授权码和收件人。")
        return False

    msg = MIMEText(message, "plain", "utf-8")
    msg["From"] = formataddr((title, sender))
    msg["To"] = formataddr(("User", receiver))
    msg["Subject"] = subject

    try:
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.login(sender, password)
            server.sendmail(sender, [receiver], msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError as err:
        logger.warning(f"邮件通知发送失败：SMTP 认证失败，请检查是否使用了邮箱授权码，而不是登录密码。({err})")
    except smtplib.SMTPServerDisconnected as err:
        logger.warning(f"邮件通知发送失败：SMTP 连接意外断开，请检查 SMTP 地址、端口以及授权码。({err})")
    except smtplib.SMTPException as err:
        logger.warning(f"邮件通知发送失败：SMTP 服务返回错误，请检查邮箱服务配置。({err})")
    except OSError as err:
        logger.warning(f"邮件通知发送失败：网络连接异常，请检查服务器地址、端口和网络环境。({err})")
    return False

