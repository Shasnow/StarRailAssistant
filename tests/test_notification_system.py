from __future__ import annotations

import smtplib

from SRACore.models.app_settings import NotificationSettings
from SRACore.notification.channels import email as email_channel
from SRACore.notification.dispatcher import NotificationDispatcher
from SRACore.notification.models import NotificationContext
from SRACore.notification import service


class _DummyChannel:
    name = "dummy"
    enabled_attr = "isWebhookEnabled"

    def __init__(self):
        self.calls = 0

    def send(self, context: NotificationContext) -> bool:
        self.calls += 1
        return context.payload.get("event") == context.title


class _RecorderDispatcher:
    def __init__(self):
        self.received: list[NotificationContext] = []

    def dispatch(self, context: NotificationContext) -> None:
        self.received.append(context)


def test_dispatcher_only_sends_enabled_channels() -> None:
    dispatcher = NotificationDispatcher()
    channel = _DummyChannel()
    dispatcher._channels = [channel]  # type: ignore[attr-defined]

    settings = NotificationSettings(isWebhookEnabled=True)
    ctx = NotificationContext(
        title="title",
        message="message",
        payload={"event": "title", "message": "message"},
        settings=settings,
    )

    dispatcher.dispatch(ctx)

    assert channel.calls == 1


def test_try_send_notification_uses_context_and_executor(monkeypatch) -> None:
    submitted: list[tuple] = []
    settings = NotificationSettings(isEnabled=True)

    monkeypatch.setattr(service, "load_notification_settings", lambda: settings)
    monkeypatch.setattr(service._notification_executor, "submit", lambda fn, ctx: submitted.append((fn, ctx)))

    service.try_send_notification("title", "message", "success")

    assert len(submitted) == 1
    _, context = submitted[0]
    assert context.title == "title"
    assert context.message == "message"
    assert context.payload["result"] == "success"


def test_try_send_notification_uses_new_dispatcher(monkeypatch) -> None:
    recorder = _RecorderDispatcher()
    monkeypatch.setattr(service, "_notification_dispatcher", recorder)
    monkeypatch.setattr(service, "load_notification_settings", lambda: NotificationSettings(isEnabled=True))
    monkeypatch.setattr(service._notification_executor, "submit", lambda fn, ctx: fn(ctx))

    service.try_send_notification("title", "message", "success")

    assert len(recorder.received) == 1
    assert recorder.received[0].title == "title"


def test_channel_test_notification_invalid_channel() -> None:
    label, ok = service.send_channel_test_notification("unknown")

    assert label == ""
    assert ok is False


def test_send_mail_handles_smtp_disconnect(monkeypatch) -> None:
    warnings: list[str] = []

    class _DisconnectedSMTP:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def login(self, *_args, **_kwargs):
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

        def sendmail(self, *_args, **_kwargs):
            raise AssertionError("sendmail should not be called after login failure")

    monkeypatch.setattr(email_channel.smtplib, "SMTP_SSL", _DisconnectedSMTP)
    monkeypatch.setattr(email_channel.logger, "warning", lambda message: warnings.append(str(message)))

    ok = email_channel.send_mail(
        title="SRA",
        subject="SRA通知",
        message="message",
        smtp_server="smtp.example.com",
        port=465,
        sender="sender@example.com",
        password="auth-code",
        receiver="receiver@example.com",
    )

    assert ok is False
    assert warnings


def test_channel_test_notification_catches_channel_exception(monkeypatch) -> None:
    warnings: list[str] = []

    class _BrokenChannel:
        name = "broken"
        enabled_attr = "isEmailEnabled"

        def send(self, _context: NotificationContext) -> bool:
            raise RuntimeError("boom")

    monkeypatch.setattr(service, "_build_channel", lambda _channel: _BrokenChannel())
    monkeypatch.setattr(service, "load_notification_settings", lambda: NotificationSettings(isEnabled=True))
    monkeypatch.setattr(service.logger, "warning", lambda message: warnings.append(str(message)))

    label, ok = service.send_channel_test_notification("email")

    assert label == "邮件"
    assert ok is False
    assert warnings
    assert "邮件 测试通知发送失败" in warnings[0]


