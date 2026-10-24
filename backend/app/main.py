"""MateAI 데이터 비서 API. 실행: backend 폴더에서 uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import chat, conversations, data
from app.services.seed import seed_if_empty
from app.services.store import store


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if config.SEED_ON_EMPTY:
        seed_if_empty(store)  # 비어 있으면 공식 통계 200개를 넣는다
    yield


app = FastAPI(
    title="MateAI 데이터 비서 API",
    description="한국관광공사 방한 입국자 월별 통계를 요약해 GPT 시스템 프롬프트에 주입하는 AI 비서 (Codyssey 미션)",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/", tags=["health"])
def root():
    return {"service": "MateAI 데이터 비서 API", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    return {"ok": True, "store": store.mode, "llm": "openai" if config.OPENAI_API_KEY else "offline"}
