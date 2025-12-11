import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(subject: str, html_body: str, recipient: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM
    message["To"] = recipient
    message.set_content("Jeśli nie widzisz wiadomości wejdź na stronę w przeglądarce.")
    message.add_alternative(html_body, subtype="html")

    smtp_class = smtplib.SMTP_SSL if settings.EMAIL_USE_SSL else smtplib.SMTP
    try:
        with smtp_class(settings.EMAIL_HOST, settings.EMAIL_PORT) as client:
            if not settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
                client.starttls()
            if settings.EMAIL_USER and settings.EMAIL_PASSWORD:
                client.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            client.send_message(message)
            logger.info("Sent email '%s' to %s", subject, recipient)
    except Exception as exc:
        logger.exception("Failed to send email '%s' to %s: %s", subject, recipient, exc)
        raise
