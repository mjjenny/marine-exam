"""Email notifications.

Currently supports SMTP. If neither SMTP nor SendGrid is configured, messages are
logged instead of sent, so signup/approval flows work end-to-end in dev without a
mail server. SendGrid can be wired in later behind the same interface.
"""
import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

logger = logging.getLogger(__name__)


def _send_smtp(to_addr: str, subject: str, body: str) -> bool:
    cfg = current_app.config
    host = cfg.get("SMTP_HOST")
    if not host:
        return False
    msg = EmailMessage()
    msg["From"] = cfg.get("MAIL_FROM")
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, cfg.get("SMTP_PORT", 587)) as server:
        server.starttls()
        if cfg.get("SMTP_USER"):
            server.login(cfg["SMTP_USER"], cfg.get("SMTP_PASSWORD", ""))
        server.send_message(msg)
    return True


def send_email(to_addr: str, subject: str, body: str) -> None:
    """Best-effort send. Falls back to logging when no transport is configured."""
    if not to_addr:
        logger.warning("send_email: no recipient; skipping (%s)", subject)
        return
    try:
        if _send_smtp(to_addr, subject, body):
            logger.info("Email sent to %s: %s", to_addr, subject)
            return
    except Exception:  # noqa: BLE001 - never let email break the request flow
        logger.exception("SMTP send failed; falling back to log")

    logger.info(
        "[EMAIL not sent — no transport configured]\nTo: %s\nSubject: %s\n\n%s",
        to_addr,
        subject,
        body,
    )


def notify_admin_new_signup(user_email: str) -> None:
    admin_addr = current_app.config.get("ADMIN_NOTIFY_EMAIL")
    send_email(
        admin_addr,
        subject="New member signup awaiting approval",
        body=(
            f"A new user has signed up and is awaiting approval:\n\n"
            f"  {user_email}\n\n"
            f"Approve or reject them from the admin queue."
        ),
    )


def notify_password_reset(user_email: str, reset_url: str) -> None:
    send_email(
        user_email,
        subject="Reset your Marine Exam Prep password",
        body=(
            "We received a request to reset your password.\n\n"
            "Click the link below to choose a new password (the link is valid for 1 hour):\n\n"
            f"  {reset_url}\n\n"
            "If you did not request this, you can safely ignore this email — your "
            "password will not be changed."
        ),
    )


def notify_user_approved(user_email: str) -> None:
    send_email(
        user_email,
        subject="Your Marine Exam Prep account is approved",
        body=(
            "Good news — your account has been approved. "
            "You can now log in and access all five subjects."
        ),
    )
