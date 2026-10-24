"""컨텍스트 주입 + 도구 호출(Function Calling).
1) 데이터 요약을 시스템 프롬프트에 넣는다. 2) 더 필요하면 GPT가 도구를 부른다.
OPENAI_API_KEY 가 없으면 요약만으로 만든 규칙 기반 답(mode=offline)을 돌려준다."""
import json
from typing import Callable, Dict, List, Tuple

from app import config

SYSTEM_TEMPLATE = """당신은 처음 한국을 찾는 여행자의 현지 호스트 '민우'이자 방한 관광 데이터 분석 비서입니다.

[사용자 데이터 요약: 한국관광공사 방한 입국자 월별 통계]
- 데이터 기간: {period}
- 총 레코드: {count}개
- 주요 지표: {metrics}
- 최신 값: {latest}
- 최근 트렌드: {trend}

규칙:
- 위 데이터를 근거로 맞춤형 답변을 하세요. 숫자를 말할 때는 몇 년 몇 월 값인지 밝히세요.
- 달별 계절성, 연도별 합계, 최근 원자료가 더 필요하면 도구를 호출하세요.
- 데이터에 없는 것은 모른다고 말하고, 지어내지 마세요.
- 한국어 질문엔 한국어, 영어 질문엔 영어로 3–6문장 안에서 답하세요."""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_data_summary",
        "description": "현재 저장된 데이터의 기간·개수·평균·최대·최소·최근 추세를 다시 조회한다.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_statistics",
        "description": "연도별 합계, 1–12월 평균(계절성), 가장 붐비는/한산한 달, 최근 24개월 전년 동월 대비 증감률.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_recent_data",
        "description": "최근 n개월의 원자료(date, value, memo: 외국인·중국·일본·미국 입국자).",
        "parameters": {"type": "object", "properties": {
            "n": {"type": "integer", "minimum": 1, "maximum": 36}}, "required": ["n"]}}},
]


def system_prompt(summary: Dict) -> str:
    return SYSTEM_TEMPLATE.format(
        period=summary.get("period"), count=summary.get("count"),
        metrics=json.dumps(summary.get("metrics"), ensure_ascii=False),
        latest=json.dumps(summary.get("latest"), ensure_ascii=False),
        trend=summary.get("trend"))


def offline_reply(question: str, summary: Dict) -> str:
    m, lt = summary.get("metrics", {}), summary.get("latest") or {}
    return (f"[오프라인 모드: OPENAI_API_KEY 없음] 저장된 데이터는 {summary.get('period')} "
            f"{summary.get('count')}개월치예요. 월평균 {m.get('average', 0):,}명, "
            f"최고 {m.get('max_date')} {m.get('max', 0):,}명, 최저 {m.get('min_date')} {m.get('min', 0):,}명이고, "
            f"최신 {lt.get('date')} {lt.get('value', 0):,}명(전년 동월 대비 {lt.get('yoy_pct')}%)입니다. "
            f"최근 추세는 {summary.get('trend')}.")


def answer(history: List[Dict], summary: Dict,
           tools_impl: Dict[str, Callable[..., Dict]]) -> Tuple[str, list, str]:
    """history: [{role, content}...] (마지막이 사용자 질문). 반환: (답, 도구 호출 기록, mode)"""
    if not config.OPENAI_API_KEY:
        return offline_reply(history[-1]["content"], summary), [], "offline"
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    msgs = [{"role": "system", "content": system_prompt(summary)}] + history[-20:]
    log = []
    for _ in range(3):  # 도구 호출 최대 3회
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL, messages=msgs, tools=TOOLS,
            max_tokens=config.MAX_TOKENS, temperature=0.4)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return (msg.content or "").strip(), log, "openai"
        msgs.append({"role": "assistant", "content": msg.content or "",
                     "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            fn = tools_impl.get(tc.function.name)
            result = fn(**args) if fn else {"error": "unknown tool"}
            log.append({"tool": tc.function.name, "args": args})
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": json.dumps(result, ensure_ascii=False)[:6000]})
    return "도구 호출이 너무 많아 답을 마치지 못했어요. 질문을 좁혀 주세요.", log, "openai"
