#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# restore_production.sh — one-command production content restore.
#
# It writes the two Python helpers (import_content.py, restore_sketches.py),
# copies them plus your content seed and sketches into the running backend
# container, then: imports all content, uploads the EK Naval sketches, and
# (re)creates your admin account.
#
# PREREQUISITES (already true if you deployed per DEPLOYMENT.md):
#   • Run from the project root.
#   • The stack is up:  docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
#   • backend/seeds/content_seed.json is present (2 MB — cannot be embedded in a
#     script; it ships in your repo) and, for sketches, backend/seeds/ek_naval_sketches/*.png.
#
# USAGE:
#   chmod +x restore_production.sh
#   ./restore_production.sh                 # prompts for admin email/password
#   ADMIN_EMAIL=you@x.com ADMIN_PASSWORD='s3cret' ./restore_production.sh   # non-interactive
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── config (override via env if needed) ──
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKEND_SVC="${BACKEND_SVC:-backend}"
SEED_DIR="backend/seeds"
COMPOSE="docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE}"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ── 0. preflight ──
[ -f "$COMPOSE_FILE" ] || die "Run this from the project root ($COMPOSE_FILE not found)."
[ -f "$ENV_FILE" ]     || die "$ENV_FILE not found. Create it from .env.prod.example first."
$COMPOSE ps --status running --services 2>/dev/null | grep -qx "$BACKEND_SVC" \
  || die "The '$BACKEND_SVC' service isn't running. Start the stack first:
    $COMPOSE up -d --build"
mkdir -p "$SEED_DIR/ek_naval_sketches"

# ── 1. write import_content.py ──
say "Writing $SEED_DIR/import_content.py"
cat > "$SEED_DIR/import_content.py" <<'PYEOF'
"""Restore exam content from content_seed.json (produced by export_content.py).

Recreates subjects, topics, diets, canonical answers and question occurrences from
natural keys, so it works on a fresh migrated database in any environment.

Per subject it does a CLEAN re-import: it deletes that subject's existing answers,
diets and topics, then re-inserts from the seed. On an empty database this simply
loads everything; on a populated one it replaces each subject's content wholesale.

    cd backend && python seeds/import_content.py            # <- seeds/content_seed.json
    cd backend && python seeds/import_content.py in.json    # custom path
"""
import json
import os
import sys
from datetime import date

from sqlalchemy import delete

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Diet, QuestionInstance, Subject, Topic

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "content_seed.json")


def run():
    with open(os.path.abspath(SRC), encoding="utf-8") as fh:
        doc = json.load(fh)

    app = create_app()
    with app.app_context():
        for sub in doc["subjects"]:
            subject = db.session.execute(
                db.select(Subject).filter_by(slug=sub["slug"])
            ).scalar_one_or_none()
            if subject is None:
                subject = Subject(slug=sub["slug"], name=sub["name"], is_oral=sub.get("is_oral", False))
                db.session.add(subject)
                db.session.flush()
            else:
                subject.name = sub["name"]
                subject.is_oral = sub.get("is_oral", False)

            # clean this subject's content (answers first -> cascades its question rows)
            db.session.execute(delete(CanonicalAnswer).where(CanonicalAnswer.subject_id == subject.id))
            db.session.execute(delete(Diet).where(Diet.subject_id == subject.id))
            db.session.execute(delete(Topic).where(Topic.subject_id == subject.id))
            db.session.flush()

            topic_row = {}
            for name in sub.get("topics", []):
                t = Topic(subject_id=subject.id, name=name)
                db.session.add(t)
                topic_row[name] = t

            diet_row = {}
            for d in sub.get("diets", []):
                dt = date.fromisoformat(d["date"]) if d.get("date") else None
                row = Diet(subject_id=subject.id, label=d["label"], date=dt,
                           sort_order=d.get("sort_order", 0))
                db.session.add(row)
                diet_row[d["label"]] = row
            db.session.flush()

            for a in sub["answers"]:
                topic = topic_row.get(a.get("topic"))
                ca = CanonicalAnswer(
                    subject_id=subject.id,
                    topic_id=topic.id if topic else None,
                    slug=a.get("slug"),
                    title=a.get("title"),
                    marks=a.get("marks"),
                    question_as_set=a.get("question_as_set"),
                    answer_text=a.get("answer_text") or "",
                    sketch_refs=a.get("sketch_refs") or [],
                )
                db.session.add(ca)
                db.session.flush()
                for o in a.get("occurrences", []):
                    diet = diet_row.get(o.get("diet"))
                    db.session.add(QuestionInstance(
                        canonical_answer_id=ca.id,
                        diet_id=diet.id if diet else None,
                        question_number=o.get("question_number"),
                        question_text_as_asked=o.get("question_text_as_asked"),
                        examiner_feedback_text=o.get("examiner_feedback_text"),
                        source=o.get("source"),
                        total_marks=o.get("total_marks"),
                        marks_parts=o.get("marks_parts"),
                    ))

        db.session.commit()

        # summary
        for sub in doc["subjects"]:
            s = db.session.execute(db.select(Subject).filter_by(slug=sub["slug"])).scalar_one()
            na = db.session.scalar(db.select(db.func.count(CanonicalAnswer.id)).where(CanonicalAnswer.subject_id == s.id))
            ni = db.session.scalar(db.select(db.func.count(QuestionInstance.id))
                                   .join(CanonicalAnswer).where(CanonicalAnswer.subject_id == s.id))
            print(f"  restored {s.name:14} answers={na:>4} questions={ni:>4}")
        print("Restore complete.")


if __name__ == "__main__":
    run()
PYEOF

# ── 2. write restore_sketches.py ──
say "Writing $SEED_DIR/restore_sketches.py"
cat > "$SEED_DIR/restore_sketches.py" <<'PYEOF'
"""Re-upload the EK Naval sketch images to object storage under the EXACT keys the
database references, so the sketch thumbnails work again after an object-storage wipe.

Run this AFTER import_content.py (the DB must already hold the EK Naval sketch_refs).
Each answer's slug (e.g. "e39") maps to its bundled PNG(s) in ek_naval_sketches/
(E39_*.png); the images are put to the storage keys stored in that answer's
sketch_refs. Idempotent — safe to re-run.

    cd backend && python seeds/restore_sketches.py
"""
import os

from app import create_app
from app.extensions import db
from app.models import CanonicalAnswer, Subject
from app.services.storage import StorageError, _bucket, _client, ensure_bucket

SKETCH_DIR = os.path.join(os.path.dirname(__file__), "ek_naval_sketches")


def run():
    app = create_app()
    with app.app_context():
        subject = db.session.execute(
            db.select(Subject).filter_by(slug="ek-naval")
        ).scalar_one_or_none()
        if subject is None:
            raise SystemExit("EK Naval subject not found — run import_content.py first.")

        try:
            ensure_bucket()
            client, bucket = _client(), _bucket()
        except StorageError as exc:
            raise SystemExit(f"Object storage is not configured ({exc}). Set STORAGE_* env vars.")

        answers = db.session.execute(
            db.select(CanonicalAnswer)
            .where(CanonicalAnswer.subject_id == subject.id)
            .order_by(CanonicalAnswer.id)
        ).scalars().all()

        uploaded, problems = 0, []
        for a in answers:
            refs = a.sketch_refs or []
            if not refs:
                continue
            code = (a.slug or "").upper()
            pngs = sorted(
                f for f in os.listdir(SKETCH_DIR)
                if f.startswith(code + "_") and f.lower().endswith(".png")
            )
            if len(pngs) != len(refs):
                problems.append(f"{a.slug}: {len(refs)} sketch_refs but {len(pngs)} PNG file(s)")
            for i, ref in enumerate(refs):
                if i >= len(pngs):
                    problems.append(f"{a.slug} ref #{i} ({ref.get('path')}): no matching PNG")
                    continue
                with open(os.path.join(SKETCH_DIR, pngs[i]), "rb") as fh:
                    client.put_object(Bucket=bucket, Key=ref["path"], Body=fh,
                                      ContentType="image/png")
                uploaded += 1

        print(f"Uploaded {uploaded} EK Naval sketch image(s) to storage.")
        if problems:
            print("Issues:")
            for p in problems:
                print(f"  - {p}")


if __name__ == "__main__":
    run()
PYEOF

# ── 3. verify the large data assets (cannot be embedded in this script) ──
[ -f "$SEED_DIR/content_seed.json" ] || die \
"$SEED_DIR/content_seed.json is missing — it can't be embedded in this script (2 MB).
    Transfer it to the server (git pull, or scp it into $SEED_DIR/) and re-run."
sketch_count=$(ls "$SEED_DIR"/ek_naval_sketches/*.png 2>/dev/null | wc -l | tr -d ' ')
[ "$sketch_count" -ge 1 ] || echo "WARNING: no PNGs in $SEED_DIR/ek_naval_sketches — EK Naval sketch upload will be skipped."

# ── 4. copy seed files into the running backend container ──
say "Copying seed files into the '$BACKEND_SVC' container"
$COMPOSE cp "$SEED_DIR/import_content.py"   "$BACKEND_SVC:/app/seeds/import_content.py"
$COMPOSE cp "$SEED_DIR/restore_sketches.py" "$BACKEND_SVC:/app/seeds/restore_sketches.py"
$COMPOSE cp "$SEED_DIR/content_seed.json"   "$BACKEND_SVC:/app/seeds/content_seed.json"
$COMPOSE exec -T "$BACKEND_SVC" mkdir -p /app/seeds/ek_naval_sketches
if [ "$sketch_count" -ge 1 ]; then
  $COMPOSE cp "$SEED_DIR/ek_naval_sketches/." "$BACKEND_SVC:/app/seeds/ek_naval_sketches/"
fi

# ── 5. import all content ──
say "Importing content (subjects, topics, diets, answers, questions)"
$COMPOSE exec -T "$BACKEND_SVC" python seeds/import_content.py

# ── 6. upload EK Naval sketches ──
if [ "$sketch_count" -ge 1 ]; then
  say "Uploading EK Naval sketch images"
  $COMPOSE exec -T "$BACKEND_SVC" python seeds/restore_sketches.py
fi

# ── 7. (re)create the admin account ──
: "${ADMIN_EMAIL:=}"
: "${ADMIN_PASSWORD:=}"
[ -n "$ADMIN_EMAIL" ]    || read -rp  "Admin email: " ADMIN_EMAIL
[ -n "$ADMIN_PASSWORD" ] || { read -rsp "Admin password: " ADMIN_PASSWORD; echo; }
say "Creating / updating admin: $ADMIN_EMAIL"
$COMPOSE exec -T "$BACKEND_SVC" flask create-admin --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD"

say "All done — content restored, sketches uploaded, admin ready. Visit your site and log in."
