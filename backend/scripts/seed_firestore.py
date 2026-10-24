"""Firestore data 컬렉션에 CSV를 한 번 넣는다. backend 폴더에서: python scripts/seed_firestore.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.seed import seed_if_empty  # noqa: E402
from app.services.store import store  # noqa: E402

print(store.mode, "에", seed_if_empty(store), "건 넣음(이미 있으면 0)")
