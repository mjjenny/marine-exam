"""Shared pytest fixtures.

Runs against a real Postgres test database (JSONB/enum types can't be mirrored on
SQLite). The DB is created if missing, tables built once per session, and truncated
between tests for isolation. Object storage is mocked in-process so sketch tests don't
require MinIO.
"""
import os
from datetime import date

import psycopg2
import pytest

from app import create_app
from app.auth import hash_password
from app.config import Config
from app.extensions import db
from app.models import (
    CanonicalAnswer,
    Diet,
    QuestionInstance,
    Subject,
    Topic,
    User,
)
from app.models.user import UserStatus

TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "marine_exam_test")
PG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "user": os.environ.get("PGUSER", "marine"),
    "password": os.environ.get("PGPASSWORD", "marine"),
}


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{PG['user']}:{PG['password']}"
        f"@{PG['host']}:{PG['port']}/{TEST_DB_NAME}"
    )
    # Force storage off at app-creation time; sketch tests monkeypatch the functions.
    STORAGE_ENDPOINT = None


def _ensure_test_database():
    conn = psycopg2.connect(dbname="postgres", **PG)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        conn.close()


@pytest.fixture(scope="session")
def app():
    _ensure_test_database()
    app = create_app(TestingConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def _clean_db(app):
    """Truncate every table before each test for isolation."""
    with app.app_context():
        tables = ", ".join(f'"{t.name}"' for t in db.metadata.sorted_tables)
        db.session.execute(db.text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        db.session.commit()
    yield


# ── user / client helpers ────────────────────────────────
@pytest.fixture
def user_factory(app):
    counter = {"n": 0}

    def _make(status="approved", is_admin=False, password="password123", email=None):
        counter["n"] += 1
        email = email or f"user{counter['n']}@test.local"
        with app.app_context():
            u = User(
                email=email,
                password_hash=hash_password(password),
                status=UserStatus(status),
                is_admin=is_admin,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        return {"id": uid, "email": email, "password": password}

    return _make


@pytest.fixture
def login(app):
    def _login(email, password="password123"):
        client = app.test_client()
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.get_data(as_text=True)
        return client

    return _login


@pytest.fixture
def anon(app):
    return app.test_client()


@pytest.fixture
def approved(user_factory, login):
    u = user_factory(status="approved")
    client = login(u["email"], u["password"])
    client.user = u
    return client


@pytest.fixture
def pending(user_factory, login):
    u = user_factory(status="pending")
    client = login(u["email"], u["password"])
    client.user = u
    return client


@pytest.fixture
def admin(user_factory, login):
    u = user_factory(status="approved", is_admin=True)
    client = login(u["email"], u["password"])
    client.user = u
    return client


# ── content fixture ──────────────────────────────────────
@pytest.fixture
def content(app):
    """A known content graph: EK Motor (2 diets, a shared fuel answer across both) and
    EK Oral (flat). Returns a dict of ids/slugs for assertions."""
    with app.app_context():
        motor = Subject(name="EK Motor", slug="ek-motor")
        oral = Subject(name="EK Oral", slug="ek-oral", is_oral=True)
        db.session.add_all([motor, oral])
        db.session.flush()

        july = Diet(subject_id=motor.id, label="July 2025", date=date(2025, 7, 1), sort_order=100)
        march = Diet(subject_id=motor.id, label="March 2025", date=date(2025, 3, 1), sort_order=99)
        db.session.add_all([july, march])
        db.session.flush()

        fuel = Topic(subject_id=motor.id, name="Fuel")
        cooling = Topic(subject_id=motor.id, name="Cooling")
        safety = Topic(subject_id=oral.id, name="Safety")
        db.session.add_all([fuel, cooling, safety])
        db.session.flush()

        fuel_answer = CanonicalAnswer(
            subject_id=motor.id, topic_id=fuel.id,
            answer_text="Original fuel answer.", sketch_refs=[],
        )
        oral_answer = CanonicalAnswer(
            subject_id=oral.id, topic_id=safety.id,
            answer_text="Original oral answer.", sketch_refs=[],
        )
        db.session.add_all([fuel_answer, oral_answer])
        db.session.flush()

        qi_july = QuestionInstance(
            canonical_answer_id=fuel_answer.id, diet_id=july.id, question_number="1",
            question_text_as_asked="Describe fuel injection timing effects.",
            examiner_feedback_text="Distinguish advanced vs retarded.",
        )
        qi_march = QuestionInstance(
            canonical_answer_id=fuel_answer.id, diet_id=march.id, question_number="3",
            question_text_as_asked="Explain fuel timing on performance.",
            examiner_feedback_text="Mention emissions.",
        )
        qi_oral = QuestionInstance(
            canonical_answer_id=oral_answer.id, diet_id=None, question_number=None,
            question_text_as_asked="Enclosed space entry: what checks are required?",
            examiner_feedback_text="Risk assessment, atmosphere testing, permit.",
        )
        db.session.add_all([qi_july, qi_march, qi_oral])
        db.session.commit()

        return {
            "motor_slug": "ek-motor",
            "oral_slug": "ek-oral",
            "july_id": july.id,
            "march_id": march.id,
            "fuel_topic_id": fuel.id,
            "safety_topic_id": safety.id,
            "fuel_answer_id": fuel_answer.id,
            "oral_answer_id": oral_answer.id,
            "qi_july_id": qi_july.id,
            "qi_march_id": qi_march.id,
            "qi_oral_id": qi_oral.id,
        }


# ── mocked object storage ────────────────────────────────
class _FakeBody:
    def __init__(self, data):
        self._data = data

    def iter_chunks(self):
        yield self._data


@pytest.fixture
def fake_storage(monkeypatch):
    """In-memory stand-in for object storage: patches the upload/get functions the
    blueprints use. Returns the backing dict {key: (bytes, content_type)}."""
    store = {}

    def fake_upload(fileobj, filename, content_type, prefix="sketches"):
        data = fileobj.read()
        key = f"{prefix}/test-{len(store)}-{filename}"
        store[key] = (data, content_type or "application/octet-stream")
        return key

    def fake_get(key):
        if key not in store:
            from app.services.storage import StorageError

            raise StorageError(f"not found: {key}")
        data, content_type = store[key]
        return _FakeBody(data), content_type

    monkeypatch.setattr("app.blueprints.suggestions.upload_fileobj", fake_upload)
    monkeypatch.setattr("app.blueprints.content.get_object", fake_get)
    return store
