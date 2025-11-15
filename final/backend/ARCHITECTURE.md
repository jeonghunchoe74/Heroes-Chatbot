# 아키텍처 문서

## 개요

이 백엔드는 **FastAPI + LangGraph + LangChain** 기반의 챗봇 시스템입니다.

주요 특징:
- **LangGraph**를 사용한 오케스트레이션
- **LangChain RAG 파이프라인** (BM25 retriever + stuff-documents chain + validator chain)
- **멘토별 에이전트** (버핏, 린치, 우드)
- **외부 REST API 통합** (Kiwoom 등)

## 주요 워크플로우

```
API/WebSocket 요청
    ↓
generate_response_unified() (unified_chatbot_service.py)
    ↓
LangGraph orchestration_graph
    ↓
START → Router → [Intent별 분기]
    ↓
    ├─→ LangChain RAG Node (philosophy 질문)
    │   ├─→ BM25 Retriever
    │   ├─→ Stuff Documents Chain (draft answer)
    │   └─→ Validator Chain (검증 + JSON 출력)
    │       ↓
    │       ├─→ 검증 실패 → Refine Node (재시도)
    │       └─→ 검증 성공 → 다음 단계
    │
    ├─→ Legacy RAG Loader (포트폴리오/매크로 데이터)
    │
    ├─→ REST API Node (Kiwoom 등, 종목 지표)
    │
    └─→ Mentor Agent Node (최종 응답 생성)
        ↓
END (응답 반환)
```

## 주요 구성 요소

### 1. LangChain RAG 파이프라인 (`app/services/langchain_rag.py`)

**역할**: 멘토 철학 데이터를 검색하고 검증된 답변을 생성

**구성 요소**:
- **BM25 Retriever**: 멘토별 철학 문서에서 관련 스니펫 검색
- **Stuff Documents Chain**: 검색된 문서를 기반으로 초안 답변 생성
- **Validator Chain**: 초안 답변을 검증하고 JSON 형식으로 결과 반환
  - `is_valid`: 검증 통과 여부
  - `final_answer`: 검증된 최종 답변
  - `confidence`: 신뢰도 (0.0-1.0)
  - `issues`: 발견된 문제점 리스트

**사용 예시**:
```python
from app.services.langchain_rag import run_rag_pipeline

result = await run_rag_pipeline(
    query="버핏의 인플레이션 관점은?",
    guru_id="buffett",
    intent=Intent.PHILOSOPHY,
    top_k=5,
)
```

### 2. LangGraph 오케스트레이션 (`app/services/orchestration_graph.py`)

**역할**: 전체 워크플로우를 오케스트레이션

**주요 노드**:
- **router_node**: Intent 라우팅
- **langchain_rag_node**: LangChain RAG 파이프라인 실행
- **refine_rag_node**: RAG 검증 실패 시 재시도
- **rag_loader_node**: 포트폴리오/매크로 데이터 로딩 (레거시)
- **rest_api_node**: 외부 API 호출 (Kiwoom 등)
- **mentor_agent_node**: 최종 응답 생성

**상태 관리**:
- `OrchestrationState` TypedDict로 상태 관리
- LangChain RAG 결과: `rag_docs`, `validated_answer`, `rag_is_valid`, `rag_confidence`, `rag_issues`
- 레거시 RAG 데이터: `philosophy_snippets`, `portfolio_history`, `macro_data`
- 외부 API 데이터: `stock_metrics`

### 3. 멘토 에이전트 (`app/mentors/`)

**역할**: 멘토별 스타일로 최종 응답 생성

**주요 파일**:
- `app/mentors/buffett_agent.py`: 워렌 버핏 에이전트
- `app/mentors/lynch_agent.py`: 피터 린치 에이전트
- `app/mentors/wood_agent.py`: 캐시 우드 에이전트
- `app/mentors/registry.py`: 에이전트 레지스트리

**입력**:
- `validated_answer`: LangChain RAG의 검증된 답변
- `portfolio_history`: 포트폴리오 히스토리
- `macro_data`: 매크로 데이터
- `stock_metrics`: 종목 지표

### 4. API 라우터 (`app/routers/chatbot_router.py`)

**주요 엔드포인트**:
- `POST /chatbot`: 메인 대화 엔드포인트 (LangGraph 기반)
- `POST /chatbot/simple`: 레거시 호환 엔드포인트
- `POST /message`: 레거시 호환 엔드포인트 (웹소켓 프론트용)
- `GET /chatbot/init/{guru_id}`: 세션 초기화
- `POST /chatbot/analyze`: 뉴스/텍스트 분석

**모든 엔드포인트는 `generate_response_unified()`를 직접 호출합니다.**

### 5. WebSocket 서버 (`app/sockets/chat_server.py`)

**변경 사항**:
- 이전: HTTP POST 요청으로 `/chatbot/` 엔드포인트 호출
- 현재: `generate_response_unified()` 직접 호출

**장점**:
- 불필요한 HTTP 호출 제거
- 더 빠른 응답 시간
- 단순한 아키텍처

## 데이터 흐름

### 1. Philosophy 질문 처리

```
사용자: "버핏의 인플레이션 관점은?"
    ↓
Router → Intent.PHILOSOPHY 감지
    ↓
LangChain RAG Node
    ├─→ BM25 Retriever: 관련 철학 스니펫 검색
    ├─→ Stuff Documents Chain: 초안 답변 생성
    └─→ Validator Chain: 검증
        ├─→ 검증 실패 → Refine Node (재시도)
        └─→ 검증 성공 → Mentor Agent
            ↓
        최종 응답: "버핏은 인플레이션을..."
```

### 2. 종목 분석 질문 처리

```
사용자: "삼성전자 분석해줘"
    ↓
Router → Intent.COMPANY_ANALYSIS 감지
    ↓
LangChain RAG Node (철학 데이터)
    ↓
Legacy RAG Loader (포트폴리오 히스토리)
    ↓
REST API Node (Kiwoom: 실시간 지표)
    ↓
Mentor Agent Node
    ├─→ validated_answer (철학 기반 분석)
    ├─→ portfolio_history (과거 보유 이력)
    └─→ stock_metrics (현재 지표)
        ↓
    최종 응답: "삼성전자는..."
```

## 의존성

### 필수 패키지
- `langchain>=0.1.0`: LangChain 코어
- `langchain-core>=0.1.0`: LangChain 코어 유틸리티
- `langchain-openai>=0.0.5`: OpenAI 통합
- `langchain-community>=0.0.20`: BM25 retriever 등 커뮤니티 통합
- `langgraph>=0.0.20`: LangGraph 오케스트레이션

### 설치
```bash
pip install -r requirements.txt
```

## 초기화

### RAG 캐시 초기화

서버 시작 시 RAG 데이터를 메모리에 로딩합니다:

```python
from app.services.rag_service import initialize_rag_cache

initialize_rag_cache()
```

**로딩되는 데이터**:
- `guru_philosophy_*.jsonl`: 멘토별 철학 문서
- `guru_portfolio_with_macro.jsonl`: 포트폴리오 히스토리
- `kr_macro_quarterly.jsonl`: 한국 매크로 데이터

## 레거시 코드

### 유지되는 레거시 기능

1. **`rag_service.py`**: 포트폴리오/매크로 데이터 로딩 (레거시 RAG)
2. **`chatbot_service.py`**: 세션 관리, 유틸리티 함수
3. **레거시 엔드포인트**: `/chatbot/simple`, `/message` (하위 호환성)

### 제거 예정

- `chatbot_service.generate_response()`: `generate_response_unified()`로 대체됨
- HTTP 기반 WebSocket 호출: 직접 호출로 변경됨

## 확장 가능성

### 새로운 멘토 추가

1. `app/mentors/{mentor_id}_agent.py` 생성
2. `app/mentors/registry.py`에 등록
3. RAG 데이터 추가: `guru_philosophy_{mentor_id}.jsonl`

### 새로운 Intent 추가

1. `app/mentors/types.py`에 Intent enum 추가
2. `app/mentors/router.py`에 라우팅 로직 추가
3. `orchestration_graph.py`에 노드 라우팅 추가

## 문제 해결

### RAG 검증 실패

- **원인**: 검색된 문서가 부족하거나 질문과 관련성이 낮음
- **해결**: `refine_rag_node`에서 더 많은 문서 검색 (top_k 증가)

### LangChain 의존성 오류

- **원인**: `requirements.txt`에 LangChain 패키지가 없음
- **해결**: `pip install -r requirements.txt` 재실행

### BM25 Retriever 초기화 실패

- **원인**: RAG 데이터 파일이 없음
- **해결**: `app/data/philosophy/` 디렉토리에 JSONL 파일 확인

