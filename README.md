# MateAI · 내 여행 데이터를 아는 AI 동행 비서

> Codyssey 미션 **「AI Agent 개발: 나만의 AI 비서 구축」** 제출 저장소 (개발자 miru, 김호연)
> 상태(2026-10-24): 설계·저장소 구성 단계. 아래 체크리스트의 `[ ]` 항목은 아직 구현 전이다.

## 1. 서비스 소개: 무엇을 해결하나

일반 챗봇은 "요즘 한국에 외국인 관광객이 늘었어? 지금 가면 붐벼?"라고 물어도 일반론만 답한다.
MateAI는 **방한 외래관광객 월별 시계열 데이터**를 분석해 요약을 만들고, 그 요약을 시스템 프롬프트에 넣어(컨텍스트 주입)
**처음 한국에 오는 여행자에게 "지금 상황을 아는" 현지 호스트(민우/Min)처럼 답하는 AI 동행 비서**다.

- 데모(기존 MateAI 웹 앱, 평가 대상): https://mateai-web-jk4v-two.vercel.app/
- 입장 플랫폼(솔루션 메이트 목록): https://trymateai.com/

## 2. 데이터 선정 (시계열, 100개 이상)

| 항목 | 내용 |
|---|---|
| 데이터 | 월별 방한 외래관광객 수 (date, value, memo) |
| 출처 | 한국관광공사 한국관광 데이터랩 / 공공데이터포털(data.go.kr) 출입국 관광통계 |
| 연동 API(기존 MateAI 엔진) | 한국관광공사 TourAPI `apis.data.go.kr/B551011/KorService2` (키 `DATA_GO_KR_SERVICE_KEY`), 서울 열린데이터광장 `openapi.seoul.go.kr:8088` (키 `SEOUL_OPEN_DATA_KEY`) |
| 범위 | 2010-01 – 최근월 (약 180개 포인트) |
| memo | 국가별 비중, 특이사항(코로나·성수기 등) |
| 요약 | 기간, 개수, 평균·최대·최소·합계, 최근 3·12개월 추세(증가/감소/유지), 전년 동월 대비 |

## 3. 기술 스택

- Backend: Python 3.10+, FastAPI, Uvicorn, Pydantic, firebase-admin, openai, python-dotenv → **Render**
- DB: Firebase **Firestore** (`data`, `conversations` 컬렉션)
- AI: OpenAI GPT API (`max_tokens` 제한)
- Frontend: 바닐라 HTML/CSS/JavaScript (프레임워크 없음) → **Vercel**

## 4. 구조

```
backend/
  app/main.py                 # FastAPI 초기화, CORS(ALLOWED_ORIGINS)
  app/routers/data.py         # /api/data CRUD + /api/data/summary
  app/routers/conversations.py
  app/routers/chat.py         # /api/chat (요약 → 시스템 프롬프트 → GPT → 자동 저장)
  app/services/firestore.py   # FIREBASE_SERVICE_ACCOUNT_JSON 으로 초기화
  app/services/summary.py     # 시계열 요약·추세 계산
  app/schemas.py              # Pydantic 모델(DataIn, ConversationIn, ChatIn)
  requirements.txt
frontend/
  index.html  style.css  app.js  config.js(API_BASE_URL)
data/
  inbound_tourists_monthly.csv
docs/screenshots/
```

## 5. API

| Method | Path | 설명 |
|---|---|---|
| POST | /api/data | 데이터 추가 (date, value, memo) |
| GET | /api/data | 목록 조회 |
| PUT | /api/data/{id} | 수정 |
| DELETE | /api/data/{id} | 삭제 |
| GET | /api/data/summary | 요약(프롬프트 주입용) |
| POST | /api/conversations | 대화 저장 |
| GET | /api/conversations | 대화 목록 (messages 미포함) |
| GET | /api/conversations/{id} | 특정 대화 전체 messages (방식 A) |
| DELETE | /api/conversations/{id} | 대화 삭제 |
| POST | /api/chat | 컨텍스트 주입 AI 대화 + 자동 저장 |

Swagger: `<백엔드 URL>/docs`

### 컨텍스트 주입 시스템 프롬프트

```
당신은 처음 한국을 찾는 여행자의 현지 호스트 '민우'입니다.
[방한 관광 데이터 요약]
- 데이터 기간: {period}
- 총 레코드: {count}개
- 주요 지표: {metrics}
- 최근 트렌드: {trend}
위 데이터를 근거로 붐빔·시기 추천 등 맞춤형 답변을 하고, 데이터에 없는 것은 모른다고 말하세요.
```

## 6. 배포 URL

| 구분 | URL |
|---|---|
| 프론트(Vercel) | (배포 후 기입) |
| 백엔드 API(Render) | (배포 후 기입) |
| Swagger | (배포 후 기입)/docs |

Render 무료 티어는 첫 요청이 30초 이상 걸릴 수 있다(콜드스타트). 프론트에 "서버를 깨우는 중" 안내를 띄운다.

## 7. 로컬 실행

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # 값 채우기
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
# 프론트: frontend/config.js 의 API_BASE_URL 을 로컬 주소로 두고 index.html 열기
```

## 8. 환경 변수 (최소 세트, 키는 코드에 넣지 않음)

| 이름 | 쓰는 곳 | 설명 |
|---|---|---|
| OPENAI_API_KEY | 백엔드 | GPT 호출 |
| FIREBASE_SERVICE_ACCOUNT_JSON | 백엔드 | 서비스 계정 JSON 문자열 |
| ALLOWED_ORIGINS | 백엔드 | CORS 허용 도메인(쉼표 구분) |
| OPENAI_MODEL | 백엔드 | 기본 모델명 |
| API_BASE_URL | 프론트(Vercel) | 백엔드 주소 |

## 9. 진행 체크리스트

- [x] 미션 분석, 데이터·구조·API 설계 (이 README)
- [ ] 데이터 수집(100개+) 및 요약 함수
- [ ] FastAPI + Firestore CRUD 5개
- [ ] 대화 기록 API 4개
- [ ] /api/chat 컨텍스트 주입 + 자동 저장
- [ ] 바닐라 프론트(채팅·데이터 관리·대화 기록·요약 카드)
- [ ] Render·Vercel 배포, 스크린샷 3장
- [ ] (보너스) Function Calling / MCP, 그래프, CSV 내보내기, 다크 모드

## 10. 제출 스크린샷

`docs/screenshots/`: ① 데이터 요약이 보이는 채팅(질문+답변) ② 데이터 관리(CRUD 1개 동작) ③ 대화 기록 불러오기
