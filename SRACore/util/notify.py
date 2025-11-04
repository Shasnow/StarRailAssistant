import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from plyer import notification

from SRACore.util import encryption


def send_windows_notification(title, message, timeout=10):
    """
    发送 Windows 系统通知
    :param title: 通知标题
    :param message: 通知内容
    :param timeout: 通知显示时长（秒）
    """
    
    # 发送通知
    notification.notify(title=title, message=message, app_name="SRA", timeout=timeout)

def send_mail_notification(title="SRA", message="", config: dict = None):
    """发送邮件通知"""
    SMTP = config["SmtpServer"]
    port = config["SmtpPort"]
    sender = config["EmailSender"]
    password = encryption.win_decryptor(config["EmailAuthCode"])
    receiver = config["EmailReceiver"]
    send_mail(title, "SRA通知", message, SMTP, port, sender, password, receiver)


def send_mail(title="SRA", subject="SRA通知", message="", SMTP="", port=465, sender="", password="", receiver=""):
    """发送邮件"""
    if SMTP=="" or sender=="" or password=="" or receiver=="":
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


class Summary:
    def __init__(self):
        self.date = None
        self.time = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.total = 0
        self.config = []
        self.warning: list[tuple] = []
        self.error: list[tuple] = []
        self.additional_info: list[tuple] = []

    def __str__(self) -> str:
        warning_str = ""
        for i in self.warning:
            warning_str += f"来源 {i[0]} 信息: {i[1]}\n"
        error_str = ""
        for i in self.error:
            error_str += f"来源 {i[0]} 信息: {i[1]}\n"
        additional_info_str = ""
        for i in self.additional_info:
            additional_info_str += f"来源 {i[0]} 信息: {i[1]}\n"
        mes = f"您好！您在 {self.date} 启动的任务已经完成！\n" \
              f"本次任务的结果如下：\n" \
              f"成功：{self.success}，失败：{self.failed}，跳过：{self.skipped}，总：{self.total}, 耗时：{self.time}秒\n" \
              f"收到警告：{len(self.warning)}, 遇到错误：{len(self.error)}\n" \
              f"细节: \n" \
              f"警告: \n{warning_str}\n" \
              f"错误: \n{error_str}\n" \
              f"附加信息: \n{additional_info_str}\n" \
              f"感谢您的使用！--SRA\n"
        return mes
