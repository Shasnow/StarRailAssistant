from plyer import notification

from SRACore.utils import Encryption

from .const import AppPath
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def send_system_notification(title="SRA", message="", timeout=3):
    """发送系统通知"""
    try:
        notification.notify(
            title=title,
            message=message,
            app_icon=AppPath + "/res/SRAicon.ico",
            timeout=timeout,
        )
    except Exception as e:
        with open("SRAlog.log", "a", encoding="utf-8") as log:
            log.write(str(e) + "\n")


def send_mail_notification(title="SRA", message="", config:dict=None):
    """发送邮件通知"""
    SMTP=config["SMTP"]
    sender=config["sender"]
    password=Encryption.win_decryptor(config["authorizationCode"])
    receiver=config["receiver"]
    send_mail(title, "SRA通知", message, SMTP, sender, password, receiver)

def send_mail(title="SRA", subject="SRA通知", message="", SMTP="", sender="", password="", receiver=""):
    """发送邮件通知"""
    try:
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['From'] = formataddr((title, sender))
        msg['To'] = formataddr(("User", receiver))
        msg['Subject'] = subject

        server = smtplib.SMTP_SSL(SMTP, 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver, ], msg.as_string())
        server.quit()
        return True
    except Exception:
        raise
