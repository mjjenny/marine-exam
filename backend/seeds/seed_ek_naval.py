"""Import the EK Naval question bank (topics + content at repo root).

See seeds/bank_import.py for the shared schema/logic. Idempotent.

    cd backend && python seeds/seed_ek_naval.py
"""
import os

from bank_import import import_bank

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def run():
    import_bank(
        "ek-naval",
        os.path.join(ROOT, "ek_naval_topics.json"),
        os.path.join(ROOT, "ek_naval_content.json"),
    )


if __name__ == "__main__":
    run()
