"""Custom Flask CLI commands."""
import click
from datetime import datetime, timedelta, timezone
from flask import Flask
from flask.cli import with_appcontext

from .auth import hash_password
from .extensions import db
from .models import User
from .models.user import UserStatus
from .services.email import (
    notify_membership_expired,
    notify_membership_expiry_reminder,
)

# Days-before-expiry thresholds at which reminder emails are sent.
_REMINDER_DAYS = [30, 7, 1]


@click.command("create-admin")
@click.option("--email", prompt=True, help="Admin email address.")
@click.password_option(help="Admin password (min 8 chars).")
@with_appcontext
def create_admin(email: str, password: str):
    """Create (or promote) an approved admin user."""
    email = email.strip().lower()
    if len(password) < 8:
        raise click.ClickException("password must be at least 8 characters")

    user = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(password))
        db.session.add(user)
        action = "created"
    else:
        user.password_hash = hash_password(password)
        action = "updated"

    user.is_admin = True
    user.status = UserStatus.approved
    user.expires_at = None  # admins never expire
    db.session.commit()
    click.echo(f"Admin {action}: {email} (approved, is_admin=True)")


@click.command("check-expiries")
@with_appcontext
def check_expiries():
    """Expire overdue memberships and send upcoming-expiry reminder emails.

    Designed to run once daily via cron.  Safe to re-run — reminders are keyed
    to the exact day window and the expiry transition only fires once.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start + timedelta(days=1)

    expired_count = 0
    reminder_counts = {d: 0 for d in _REMINDER_DAYS}

    # 1. Mark past-due approved users as expired and email them.
    overdue = db.session.execute(
        db.select(User).where(
            User.status == UserStatus.approved,
            User.expires_at != None,       # noqa: E711
            User.expires_at < today_start,
            User.is_admin == False,        # noqa: E712
        )
    ).scalars().all()

    for user in overdue:
        user.status = UserStatus.expired
        try:
            notify_membership_expired(user.email)
        except Exception:  # noqa: BLE001
            click.echo(f"  [warn] Could not email {user.email} on expiry")
        expired_count += 1

    if expired_count:
        db.session.commit()
        click.echo(f"Expired {expired_count} account(s).")

    # 2. Send reminder emails for accounts expiring in exactly 30 / 7 / 1 days.
    for days in _REMINDER_DAYS:
        window_start = today_start + timedelta(days=days)
        window_end   = today_end   + timedelta(days=days)

        due_soon = db.session.execute(
            db.select(User).where(
                User.status == UserStatus.approved,
                User.expires_at != None,           # noqa: E711
                User.expires_at >= window_start,
                User.expires_at <  window_end,
                User.is_admin == False,            # noqa: E712
            )
        ).scalars().all()

        for user in due_soon:
            try:
                notify_membership_expiry_reminder(user.email, days)
                reminder_counts[days] += 1
            except Exception:  # noqa: BLE001
                click.echo(f"  [warn] Could not send {days}-day reminder to {user.email}")

    for days, n in reminder_counts.items():
        if n:
            click.echo(f"Sent {n} reminder(s) for memberships expiring in {days} day(s).")

    click.echo("check-expiries complete.")


@click.command("seed-e2e")
@with_appcontext
def seed_e2e():
    """Upsert deterministic users + sample content for Playwright E2E tests."""
    from datetime import datetime, timedelta, timezone

    from .models import CanonicalAnswer, Subject
    from .models.user import MEMBERSHIP_DAYS

    specs = [
        {
            "email": "admin@e2e.local",
            "password": "E2eAdmin1!",
            "is_admin": True,
            "status": UserStatus.approved,
            "expires_at": None,
        },
        {
            "email": "member@e2e.local",
            "password": "E2eMember1!",
            "is_admin": False,
            "status": UserStatus.approved,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=MEMBERSHIP_DAYS),
        },
        {
            "email": "revoked@e2e.local",
            "password": "E2eRevoked1!",
            "is_admin": False,
            "status": UserStatus.revoked,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=100),
        },
        {
            "email": "searchable@e2e.local",
            "password": "E2eSearch1!",
            "is_admin": False,
            "status": UserStatus.approved,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=MEMBERSHIP_DAYS),
        },
    ]

    for spec in specs:
        user = db.session.execute(
            db.select(User).filter_by(email=spec["email"])
        ).scalar_one_or_none()
        if user is None:
            user = User(email=spec["email"], password_hash=hash_password(spec["password"]))
            db.session.add(user)
            action = "created"
        else:
            user.password_hash = hash_password(spec["password"])
            action = "updated"
        user.is_admin = spec["is_admin"]
        user.status = spec["status"]
        user.expires_at = spec["expires_at"]
        click.echo(f"E2E user {action}: {spec['email']} ({spec['status'].value})")

    # Minimal subject + answer so bookmark / progress E2E has a real content page.
    subject = db.session.execute(
        db.select(Subject).filter_by(slug="e2e-motor")
    ).scalar_one_or_none()
    if subject is None:
        subject = Subject(name="E2E Motor", slug="e2e-motor")
        db.session.add(subject)
        db.session.flush()
        click.echo("E2E subject created: e2e-motor")
    answer = db.session.execute(
        db.select(CanonicalAnswer).filter_by(slug="e2e-sample-answer")
    ).scalar_one_or_none()
    if answer is None:
        answer = CanonicalAnswer(
            subject_id=subject.id,
            topic_id=None,
            slug="e2e-sample-answer",
            title="E2E sample answer",
            question_as_set="What is the E2E sample question?",
            answer_text="This is a seeded answer for Playwright bookmark tests.",
            sketch_refs=[],
        )
        db.session.add(answer)
        db.session.flush()
        click.echo(f"E2E answer created: id={answer.id}")
    else:
        click.echo(f"E2E answer ready: id={answer.id}")

    db.session.commit()
    click.echo("seed-e2e complete.")


def register_cli(app: Flask) -> None:
    app.cli.add_command(create_admin)
    app.cli.add_command(check_expiries)
    app.cli.add_command(seed_e2e)
