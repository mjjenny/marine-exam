# Marine Engineer Exam Prep Platform

Membership-gated web platform for MCA/SQA Chief Engineer exam preparation across five subjects
(EK Motor, EK General, EK Naval, EK Electrical, EK Oral). See
[marine-exam-platform-spec.md](marine-exam-platform-spec.md) for the full spec.

## Stack

- **Backend:** Flask (app factory) + SQLAlchemy + Flask-Migrate (Alembic) + Postgres
- **Frontend:** React + Vite + React Router
- **Object storage:** DigitalOcean Spaces (S3 API); MinIO stands in locally
- **Email:** SMTP / SendGrid for approval notifications

## Repository layout

```
backend/    Flask API, models, Alembic migrations, dev seeds
frontend/   Vite + React SPA
docker-compose.yml   Local Postgres (+ optional MinIO)
```

## Local setup

1. Copy env template and fill in values:
   ```bash
   cp .env.example .env
   ```
2. Start Postgres:
   ```bash
   docker compose up -d db
   ```
3. Backend:
   ```bash
   cd backend
   python -m venv .venv && . .venv/Scripts/activate   # Windows; use .venv/bin/activate on *nix
   pip install -e .
   flask db upgrade
   python seeds/seed_dev.py
   flask run
   ```
4. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Tests

Backend tests use pytest against a real Postgres test database (`marine_exam_test`,
created automatically) with object storage mocked in-process — so only Postgres needs
to be running, not MinIO.

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Coverage: auth + approval gate, content routes, admin approval queue, suggest-improvement
submission, moderation + `answer_history` versioning, and sketch upload/serving.

## Build status

Step 1 (of the spec's build order) is scaffolded: **project structure + the initial schema migration
(nine tables, two enums)**. Auth, content routes, admin queues, and the suggest-improvement flow are
subsequent steps.
