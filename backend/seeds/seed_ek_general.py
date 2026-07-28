"""Import the EK General question bank (topics + content at repo root).

Same schema/logic as EK Naval — see seeds/bank_import.py. Idempotent.

    cd backend && python seeds/seed_ek_general.py
"""
import os

from bank_import import import_bank

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def run():
    import_bank(
        "ek-general",
        os.path.join(ROOT, "ek_general_topics.json"),
        os.path.join(ROOT, "ek_general_content.json"),
    )


if __name__ == "__main__":
    run()
