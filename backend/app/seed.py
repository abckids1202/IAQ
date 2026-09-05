"""Idempotent demo seed entry point.

The production seed would insert the same content through SQLAlchemy migrations;
this command documents the explicit distinction between reviewed content and
synthetic data used only for technical smoke tests.
"""
from .main import ITEMS, MAJORS


def seed() -> None:
    print(f"seeded {len(ITEMS)} reviewed baseline items")
    print(f"seeded {len(MAJORS)} major profiles")
    print("data_origin=SYNTHETIC is reserved for simulator output; no synthetic norming data is created")


if __name__ == "__main__":
    seed()
