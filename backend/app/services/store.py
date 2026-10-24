"""저장소. FIREBASE_SERVICE_ACCOUNT_JSON(또는 _PATH)이 있으면 Firestore,
없으면 로컬 시험용 메모리 저장소(서버를 끄면 사라짐, /health 의 store 로 표시)."""
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    mode = "memory"

    def __init__(self):
        self.cols: Dict[str, Dict[str, dict]] = {"data": {}, "conversations": {}}

    def list(self, col: str) -> List[dict]:
        return [{"id": k, **v} for k, v in self.cols[col].items()]

    def get(self, col: str, id_: str) -> Optional[dict]:
        v = self.cols[col].get(id_)
        return {"id": id_, **v} if v is not None else None

    def add(self, col: str, doc: dict) -> dict:
        id_ = uuid.uuid4().hex[:20]
        self.cols[col][id_] = {**doc, "created_at": _now(), "updated_at": _now()}
        return self.get(col, id_)

    def update(self, col: str, id_: str, patch: dict) -> Optional[dict]:
        if id_ not in self.cols[col]:
            return None
        self.cols[col][id_].update({**patch, "updated_at": _now()})
        return self.get(col, id_)

    def delete(self, col: str, id_: str) -> bool:
        return self.cols[col].pop(id_, None) is not None

    def bulk_add(self, col: str, docs: List[dict]) -> int:
        for d in docs:
            self.add(col, d)
        return len(docs)


class FirestoreStore:
    mode = "firestore"

    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore

        if config.FIREBASE_SERVICE_ACCOUNT_JSON:
            cred = credentials.Certificate(json.loads(config.FIREBASE_SERVICE_ACCOUNT_JSON))
        else:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_PATH)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def list(self, col: str) -> List[dict]:
        return [{"id": d.id, **d.to_dict()} for d in self.db.collection(col).stream()]

    def get(self, col: str, id_: str) -> Optional[dict]:
        d = self.db.collection(col).document(id_).get()
        return {"id": d.id, **d.to_dict()} if d.exists else None

    def add(self, col: str, doc: dict) -> dict:
        ref = self.db.collection(col).document()
        ref.set({**doc, "created_at": _now(), "updated_at": _now()})
        return self.get(col, ref.id)

    def update(self, col: str, id_: str, patch: dict) -> Optional[dict]:
        ref = self.db.collection(col).document(id_)
        if not ref.get().exists:
            return None
        ref.update({**patch, "updated_at": _now()})
        return self.get(col, id_)

    def delete(self, col: str, id_: str) -> bool:
        ref = self.db.collection(col).document(id_)
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    def bulk_add(self, col: str, docs: List[dict]) -> int:
        batch, n = self.db.batch(), 0
        for d in docs:
            batch.set(self.db.collection(col).document(), {**d, "created_at": _now(), "updated_at": _now()})
            n += 1
            if n % 400 == 0:
                batch.commit()
                batch = self.db.batch()
        batch.commit()
        return n


def make_store():
    if config.FIREBASE_SERVICE_ACCOUNT_JSON or config.FIREBASE_SERVICE_ACCOUNT_PATH:
        return FirestoreStore()
    return MemoryStore()


store = make_store()
