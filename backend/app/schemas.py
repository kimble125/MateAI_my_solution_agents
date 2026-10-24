"""Pydantic 요청·응답 모델. 잘못된 입력은 FastAPI가 422로 막는다."""
from datetime import date as Date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DataIn(BaseModel):
    date: Date = Field(..., description="YYYY-MM-DD (월별 데이터는 1일)")
    value: float = Field(..., ge=0, le=1e10, description="방한 입국자 수(명)")
    memo: str = Field("", max_length=500)


class DataUpdate(BaseModel):
    date: Optional[Date] = None
    value: Optional[float] = Field(None, ge=0, le=1e10)
    memo: Optional[str] = Field(None, max_length=500)


class DataOut(BaseModel):
    id: str
    date: str
    value: float
    memo: str = ""


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class ConversationIn(BaseModel):
    title: str = Field("새 대화", max_length=100)
    messages: List[Message] = Field(default_factory=list, max_length=200)


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class ChatOut(BaseModel):
    conversation_id: str
    reply: str
    summary: dict
    tool_calls: list = []
    mode: str
