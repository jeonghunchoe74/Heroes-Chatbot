#!/bin/bash

# 환경변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# FastAPI 서버 실행
uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --reload

