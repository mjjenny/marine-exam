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
