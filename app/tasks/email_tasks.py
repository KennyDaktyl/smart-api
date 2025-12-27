import logging

from app.celery_app import celery_app
from smart_common.core.config import settings
from smart_common.utils.emails.email_client import send_email


logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 10},
    retry_backoff=True,
)
def send_confirmation_email_task(self, email: str, token: str) -> None:
    confirm_link = f"{settings.FRONTEND_URL.rstrip('/')}/confirm-email?token={token}"

    logger.info("Sending confirmation email to %s", email)
    send_email(
        recipient=email,
        subject="Potwierdź e-mail – Smart Energy",
        template_name="confirm_email.html",
        context={
            "confirm_link": confirm_link,
            "token": token,
        },
    )

    logger.info("Confirmation email queued for %s", email)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 10},
    retry_backoff=True,
)
def send_password_reset_email_task(self, email: str, token: str) -> None:
    reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"

    logger.info("Sending password reset email to %s", email)
    send_email(
        recipient=email,
        subject="Reset hasła – Smart Energy",
        template_name="password_reset.html",
        context={
            "reset_link": reset_link,
            "token": token,
        },
    )

    logger.info("Password reset email queued for %s", email)
