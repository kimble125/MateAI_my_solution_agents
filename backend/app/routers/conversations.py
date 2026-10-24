from fastapi import APIRouter, HTTPException

from app.schemas import ConversationIn
from app.services.store import store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
COL = "conversations"


@router.post("", status_code=201, summary="대화 저장")
def create_conversation(body: ConversationIn):
    return store.add(COL, {"title": body.title, "messages": [m.model_dump() for m in body.messages]})


@router.get("", summary="대화 목록(messages 미포함, 최근 수정순)")
def list_conversations():
    items = [{"id": c["id"], "title": c.get("title", ""), "message_count": len(c.get("messages", [])),
              "created_at": c.get("created_at"), "updated_at": c.get("updated_at")}
             for c in store.list(COL)]
    return sorted(items, key=lambda c: c["updated_at"] or "", reverse=True)


@router.get("/{id}", summary="특정 대화 전체 messages (방식 A)")
def get_conversation(id: str):
    c = store.get(COL, id)
    if c is None:
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    return c


@router.delete("/{id}", summary="대화 삭제")
def delete_conversation(id: str):
    if not store.delete(COL, id):
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    return {"deleted": id}
