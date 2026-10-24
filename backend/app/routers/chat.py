from fastapi import APIRouter, HTTPException

from app.routers.data import all_rows
from app.schemas import ChatIn, ChatOut
from app.services import llm
from app.services.store import store
from app.services.summary import build_statistics, build_summary, recent_rows

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatOut, summary="컨텍스트 주입 AI 대화 + 자동 저장")
def chat(body: ChatIn):
    # 1) 데이터 요약 조회 (/api/data/summary 와 같은 함수)
    rows = all_rows()
    summary = build_summary(rows)
    # 2) 이어지는 대화면 이전 messages 불러오기
    conv = None
    if body.conversation_id:
        conv = store.get("conversations", body.conversation_id)
        if conv is None:
            raise HTTPException(404, "대화를 찾을 수 없습니다")
    history = list(conv.get("messages", [])) if conv else []
    history.append({"role": "user", "content": body.message})
    # 3) 요약을 시스템 프롬프트에 넣고 GPT 호출 (필요하면 도구 호출)
    tools_impl = {
        "get_data_summary": lambda: summary,
        "get_statistics": lambda: build_statistics(rows),
        "get_recent_data": lambda n=12: {"rows": recent_rows(rows, int(n))},
    }
    try:
        reply, tool_log, mode = llm.answer(history, summary, tools_impl)
    except Exception as e:  # OpenAI 오류는 502로 알린다(키 값은 응답에 넣지 않음)
        raise HTTPException(502, f"AI 호출 실패: {type(e).__name__}")
    history.append({"role": "assistant", "content": reply})
    # 4) conversations 에 자동 저장
    if conv:
        store.update("conversations", conv["id"], {"messages": history})
        cid = conv["id"]
    else:
        cid = store.add("conversations", {"title": body.message[:30], "messages": history})["id"]
    return ChatOut(conversation_id=cid, reply=reply, summary=summary, tool_calls=tool_log, mode=mode)
