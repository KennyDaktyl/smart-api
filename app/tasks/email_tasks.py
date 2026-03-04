import logging
import smtplib

from email_validator import EmailNotValidError, validate_email

from app.celery_app import celery_app
from smart_common.core.config import settings
from smart_common.utils.emails.email_client import send_email


logger = logging.getLogger(__name__)


def _is_valid_recipient(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError as exc:
        logger.warning(
            "Skipping email task due to invalid recipient=%s reason=%s", email, exc
        )
        return False


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 10},
    retry_backoff=True,
)
def send_confirmation_email_task(self, email: str, token: str) -> None:
    if not _is_valid_recipient(email):
        return

    confirm_link = f"{settings.FRONTEND_URL.rstrip('/')}/confirm-email?token={token}"

    logger.info("Sending confirmation email to %s", email)
    try:
        send_email(
            recipient=email,
            subject="Potwierdź e-mail – Smart Energy",
            template_name="confirm_email.html",
            context={
                "confirm_link": confirm_link,
                "token": token,
            },
        )
    except smtplib.SMTPRecipientsRefused:
        logger.warning("Confirmation email recipient refused by SMTP: %s", email)
        return
    except smtplib.SMTPResponseException as exc:
        if 500 <= exc.smtp_code < 600:
            logger.warning(
                "Confirmation email permanently rejected by SMTP code=%s recipient=%s",
                exc.smtp_code,
                email,
            )
            return
        raise

    logger.info("Confirmation email queued for %s", email)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 10},
    retry_backoff=True,
)
def send_password_reset_email_task(self, email: str, token: str) -> None:
    if not _is_valid_recipient(email):
        return

    reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"

    logger.info("Sending password reset email to %s", email)
    try:
        send_email(
            recipient=email,
            subject="Reset hasła – Smart Energy",
            template_name="password_reset.html",
            context={
                "reset_link": reset_link,
                "token": token,
            },
        )
    except smtplib.SMTPRecipientsRefused:
        logger.warning("Password reset email recipient refused by SMTP: %s", email)
        return
    except smtplib.SMTPResponseException as exc:
        if 500 <= exc.smtp_code < 600:
            logger.warning(
                "Password reset email permanently rejected by SMTP code=%s recipient=%s",
                exc.smtp_code,
                email,
            )
            return
        raise

    logger.info("Password reset email queued for %s", email)
