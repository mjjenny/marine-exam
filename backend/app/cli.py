"""Custom Flask CLI commands."""
import click
from flask import Flask
from flask.cli import with_appcontext

from .auth import hash_password
from .extensions import db
from .models import User
from .models.user import UserStatus


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
    db.session.commit()
    click.echo(f"Admin {action}: {email} (approved, is_admin=True)")


def register_cli(app: Flask) -> None:
    app.cli.add_command(create_admin)
