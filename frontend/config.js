// Vercel 빌드 때 환경 변수 API_BASE_URL 로 덮어쓴다(vercel.json buildCommand). 로컬 기본값:
window.API_BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8000";
