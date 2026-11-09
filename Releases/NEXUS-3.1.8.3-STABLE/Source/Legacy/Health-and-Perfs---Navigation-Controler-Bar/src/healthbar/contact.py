"""Prepared SMTP adapter. No automatic mail, tracking or implicit collection."""
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int
    sender: str
    recipient: str
    username: str = ""


def send_feedback(config, subject, body, password="", *, confirmed=False):
    if not confirmed:
        raise ValueError("L’envoi exige une confirmation explicite du message et du destinataire")
    if not all((config.host, config.sender, config.recipient)):
        raise ValueError("Le service de contact n’est pas encore configuré")
    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = config.recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(config.host, config.port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        if config.username:
            smtp.login(config.username, password)
        smtp.send_message(message)
