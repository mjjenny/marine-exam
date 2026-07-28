"""Application configuration, loaded from environment (.env in dev)."""
import os

from dotenv import load_dotenv

# Load repo-root .env if present, then backend-local .env (backend wins).
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://marine:marine@localhost:5432/marine_exam",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session cookie (SPA reaches the API same-origin via the Vite proxy)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set True in production (HTTPS). Off in dev so cookies work over http://localhost.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "").lower() == "true"

    # Cap request bodies (sketch uploads); per-file limit enforced in storage service.
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB

    # Object storage (DigitalOcean Spaces / local MinIO)
    STORAGE_ENDPOINT = os.environ.get("STORAGE_ENDPOINT")
    STORAGE_REGION = os.environ.get("STORAGE_REGION")
    STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET")
    STORAGE_ACCESS_KEY = os.environ.get("STORAGE_ACCESS_KEY")
    STORAGE_SECRET_KEY = os.environ.get("STORAGE_SECRET_KEY")

    # Email
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL")
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@marine-exam.local")

    # Public base URL used to build links in emails (password-reset). In production set
    # this to your site, e.g. https://your-domain.com. Falls back to the request host.
    APP_BASE_URL = os.environ.get("APP_BASE_URL")
