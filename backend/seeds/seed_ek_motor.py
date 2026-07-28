"""Import the EK Motor question bank (topics + a corpus split across 13 content files).

Same schema/logic as EK Naval/General — see seeds/bank_import.py. The corpus is
delivered as ek_motor_content_*.json at repo root; they're merged on import.
Idempotent (clean re-import). Replaces the placeholder EK Motor dev-seed data.

    cd backend && python seeds/seed_ek_motor.py
"""
import glob
import os

from bank_import import import_bank

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def run():
    content_files = sorted(glob.glob(os.path.join(ROOT, "ek_motor_content_*.json")))
    if not content_files:
        raise SystemExit("no ek_motor_content_*.json files found at repo root.")
    import_bank(
        "ek-motor",
        os.path.join(ROOT, "ek_motor_topics.json"),
        content_files,
    )


if __name__ == "__main__":
    run()
