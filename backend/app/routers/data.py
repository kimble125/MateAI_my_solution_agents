import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.schemas import DataIn, DataOut, DataUpdate
from app.services.store import store
from app.services.summary import build_statistics, build_summary

router = APIRouter(prefix="/api/data", tags=["data"])
COL = "data"


def _clean(d: dict) -> dict:
    return {"id": d["id"], "date": str(d["date"])[:10], "value": float(d["value"]), "memo": d.get("memo", "")}


def all_rows():
    return sorted((_clean(d) for d in store.list(COL)), key=lambda r: r["date"])


# 고정 경로(/summary 등)를 /{id} 보다 먼저 둔다.
@router.get("/summary", summary="데이터 요약(프롬프트 주입용)")
def get_summary():
    return build_summary(all_rows())


@router.get("/statistics", summary="추가 지표: 연도별·달별·전년 동월 대비")
def get_statistics():
    return build_statistics(all_rows())


@router.get("/export", summary="CSV 또는 JSON 내보내기")
def export(format: str = Query("csv", pattern="^(csv|json)$")):
    rows = all_rows()
    if format == "json":
        return Response(json.dumps(rows, ensure_ascii=False, indent=1), media_type="application/json",
                        headers={"Content-Disposition": "attachment; filename=data.json"})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["id", "date", "value", "memo"])
    w.writeheader()
    w.writerows(rows)
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=data.csv"})


@router.get("", response_model=list[DataOut], summary="데이터 목록")
def list_data(limit: int = Query(500, ge=1, le=2000)):
    return all_rows()[-limit:]


@router.post("", response_model=DataOut, status_code=201, summary="데이터 추가")
def create_data(body: DataIn):
    return _clean(store.add(COL, {"date": body.date.isoformat(), "value": body.value, "memo": body.memo}))


@router.put("/{id}", response_model=DataOut, summary="데이터 수정")
def update_data(id: str, body: DataUpdate):
    patch = {k: (v.isoformat() if k == "date" else v) for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(400, "바꿀 값이 없습니다")
    doc = store.update(COL, id, patch)
    if doc is None:
        raise HTTPException(404, "데이터를 찾을 수 없습니다")
    return _clean(doc)


@router.delete("/{id}", summary="데이터 삭제")
def delete_data(id: str):
    if not store.delete(COL, id):
        raise HTTPException(404, "데이터를 찾을 수 없습니다")
    return {"deleted": id}
