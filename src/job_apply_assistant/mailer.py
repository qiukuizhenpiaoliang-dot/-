from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import mimetypes
from pathlib import Path
import smtplib
from typing import Dict, Optional

from .config import Settings, resolve_path


class MailerError(RuntimeError):
    pass


@dataclass
class SendResult:
    to_email: str
    subject: str
    attachment_name: str
    message_id: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "to_email": self.to_email,
            "subject": self.subject,
            "attachment_name": self.attachment_name,
            "message_id": self.message_id,
        }


def validate_email(value: str) -> str:
    email = (value or "").strip()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise MailerError("请填写有效的 HR 接收邮箱。")
    return email


def build_message(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
) -> EmailMessage:
    recipient = validate_email(to_email)
    sender_email = settings.sender_email or settings.smtp_username
    if not sender_email:
        raise MailerError("缺少发件邮箱，请配置 SENDER_EMAIL 或 SMTP_USERNAME。")
    if not subject.strip():
        raise MailerError("邮件标题不能为空。")
    if not body.strip():
        raise MailerError("邮件正文不能为空。")

    resume_value = attachment_path or settings.resume_path
    if not resume_value:
        raise MailerError("缺少简历附件路径，请配置 RESUME_PATH 或在页面填写。")
    resume_path = resolve_path(resume_value)
    if not resume_path.exists() or not resume_path.is_file():
        raise MailerError(f"简历附件不存在：{resume_path}")

    message_id = make_msgid()
    msg = EmailMessage()
    msg["From"] = formataddr((settings.sender_name, sender_email))
    msg["To"] = recipient
    msg["Subject"] = subject.strip()
    msg["Message-ID"] = message_id
    msg.set_content(body.strip())

    mime_type, _ = mimetypes.guess_type(str(resume_path))
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    msg.add_attachment(
        resume_path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=resume_path.name,
    )
    return msg


def send_mail(
    *,
    settings: Settings,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
) -> SendResult:
    if not settings.smtp_host:
        raise MailerError("缺少 SMTP_HOST。")
    if not settings.smtp_username:
        raise MailerError("缺少 SMTP_USERNAME。")
    if not settings.smtp_password:
        raise MailerError("缺少 SMTP_PASSWORD。")

    msg = build_message(
        settings=settings,
        to_email=to_email,
        subject=subject,
        body=body,
        attachment_path=attachment_path,
    )

    if settings.smtp_use_ssl:
        client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30)
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)

    try:
        client.ehlo()
        if settings.smtp_starttls and not settings.smtp_use_ssl:
            client.starttls()
            client.ehlo()
        client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(msg)
    finally:
        client.quit()

    attachment = msg.get_payload()[-1]
    filename = attachment.get_filename() or ""
    return SendResult(
        to_email=validate_email(to_email),
        subject=subject.strip(),
        attachment_name=filename,
        message_id=str(msg["Message-ID"]),
    )
