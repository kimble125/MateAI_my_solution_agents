"""data/inbound_visitors_monthly.csv(한국관광공사 공식 통계, 200개)를 data 컬렉션에 넣는다."""
import csv
from pathlib import Path

_HERE = Path(__file__).resolve()
# backend/data(배포 루트가 backend일 때) → 저장소 루트 data 순서로 찾는다
CSV_PATH = next((p for p in (_HERE.parents[2] / "data" / "inbound_visitors_monthly.csv",
                             _HERE.parents[3] / "data" / "inbound_visitors_monthly.csv") if p.exists()),
                _HERE.parents[2] / "data" / "inbound_visitors_monthly.csv")


def load_csv(path: Path = CSV_PATH):
    with open(path, encoding="utf-8") as f:
        return [{"date": r["date"], "value": float(r["value"]), "memo": r.get("memo", "")}
                for r in csv.DictReader(f)]


def seed_if_empty(store) -> int:
    if store.list("data") or not CSV_PATH.exists():
        return 0
    return store.bulk_add("data", load_csv())
