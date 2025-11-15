# 백엔드 리팩터링 요약

## 완료된 작업

### 1. 새로운 서비스 레이어 생성

#### `app/services/intent_service.py`
- **역할**: Intent 추론, 심볼 추출, region 감지, metric 키워드 추출
- **주요 함수**:
  - `detect_intent(message: str) -> Intent`: 사용자 의도 분류
  - `extract_symbols(message: str) -> List[str]`: 종목명/티커 추출
  - `detect_region_or_market(message: str) -> Optional[str]`: KR/US 감지
  - `extract_requested_metrics(message: str) -> Set[str]`: 요청된 지표 추출
  - `extract_topic_keywords(message: str) -> List[str]`: RAG 필터링용 키워드 추출

#### `app/services/llm_service.py`
- **역할**: 모든 LLM 호출 전담
- **주요 함수**:
  - `invoke_llm()`: LangChain ChatOpenAI 사용
  - `invoke_llm_direct()`: OpenAI 클라이언트 직접 사용 (구조화된 응답용)
  - `get_model_for_guru()`: 멘토별 모델명 반환
- **장점**: 모델 변경 시 이 모듈만 수정하면 됨

#### `app/services/agent_service.py`
- **역할**: 멘토별 Agent 설정 및 전략 정의
- **주요 구조**:
  - `MentorAgentConfig`: 멘토별 설정 (스타일, 선호 섹터, 투자 시계 등)
  - `IntentStrategy`: Intent별 RAG/REST 사용 전략
  - `get_agent_config(guru_id)`: 멘토별 설정 반환
- **지원 멘토**: buffett, lynch, wood

#### `app/services/unified_chatbot_service.py`
- **역할**: 새로운 Agent + RAG + REST 구조를 사용하는 통합 서비스
- **주요 함수**:
  - `generate_response_unified()`: 새로운 구조로 응답 생성
- **특징**:
  - Intent 기반으로 필요한 RAG/REST만 선택적으로 사용
  - Agent 설정에 따라 system prompt 자동 구성

### 2. RAG 서비스 개선 (이전 작업)

#### `app/services/rag_service.py`
- **초기 로딩 캐시 구조**: 서버 시작 시 한 번만 파일 로딩
- **Intent 기반 필터링**: 
  - `get_guru_philosophy_snippets()`: Intent/topic 기반 필터링
  - `get_portfolio_history_snippets()`: symbol/period 기반 필터링
  - `get_macro_regime_snippets()`: 최근 N개만 반환
- **성능 개선**: 매 요청마다 전체 파일을 읽지 않음

### 3. 기존 코드 호환성 유지

#### `app/services/chatbot_service.py`
- `generate_response()` 함수에 `use_unified` 파라미터 추가
- 환경변수 `USE_UNIFIED_CHATBOT=true`로 새 구조 활성화 가능
- 기본값은 기존 로직 사용 (하위 호환성 유지)

## 아키텍처 구조

```
┌─────────────────────────────────────────┐
│         FastAPI Router Layer            │
│  (chatbot_router.py - 기존 스펙 유지)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Chatbot Service Layer              │
│  (chatbot_service.py / unified_*)       │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
┌───────▼───┐ ┌──▼───┐ ┌───▼────┐
│  Agent   │ │ RAG  │ │ REST   │
│ Service  │ │Service│ │Service │
└──────┬───┘ └──┬───┘ └───┬────┘
       │        │         │
       │        │         │
┌──────▼───┐ ┌──▼───┐ ┌───▼────┐
│Intent    │ │JSONL │ │Kiwoom  │
│Service   │ │Files │ │API     │
└──────────┘ └──────┘ └────────┘
```

## Intent별 데이터 소스 매트릭스

| Intent | Philosophy | Portfolio | Macro | Kiwoom | News |
|--------|-----------|-----------|-------|--------|------|
| smalltalk | 1-2 | - | - | - | - |
| stock_metrics | 1-2 | - | - | ✓ | - |
| stock_analysis | 3-5 | 2-3 | 선택적 | ✓ | - |
| stock_comparison | 3-5 | 2-3 | - | ✓ | - |
| macro_outlook | - | - | 4 | - | - |
| news_analysis | 3-5 | 2-3 | 선택적 | - | ✓ |
| research_analysis | 3-5 | - | - | - | - |

## 사용 방법

### 1. 기존 방식 (기본값)
```python
# 환경변수 설정 없이 사용하면 기존 로직 사용
response, session_id = await generate_response(
    user_input="삼성전자 현재가 얼마야?",
    guru_id="buffett"
)
```

### 2. 새로운 통합 서비스 사용
```python
# 방법 1: 환경변수 설정
# .env 파일에 추가:
# USE_UNIFIED_CHATBOT=true

# 방법 2: 코드에서 직접 지정
response, session_id = await generate_response(
    user_input="삼성전자 현재가 얼마야?",
    guru_id="buffett",
    use_unified=True
)

# 방법 3: unified 서비스 직접 호출
from app.services.unified_chatbot_service import generate_response_unified
response, session_id = await generate_response_unified(
    user_message="삼성전자 현재가 얼마야?",
    guru_id="buffett"
)
```

## 주요 개선사항

### 1. 성능
- **이전**: 매 요청마다 5103 rows (philosophy) + 56 rows (portfolio) + 98 rows (macro) 로딩
- **이후**: 서버 시작 시 1회만 로딩, 이후 메모리 캐시에서 필터링만 수행

### 2. 정확성
- Intent 기반 필터링으로 관련성 높은 데이터만 사용
- Topic keywords 기반 관련성 점수 계산

### 3. 유지보수성
- 레이어 분리로 책임 명확화
- 모델 변경 시 `llm_service.py`만 수정
- Agent 설정 변경 시 `agent_service.py`만 수정

### 4. 확장성
- 새로운 Intent 추가 시 `agent_service.py`에 전략만 추가
- 새로운 RAG 소스 추가 시 `rag_service.py`에 함수만 추가
- 새로운 REST API 추가 시 해당 서비스에 함수만 추가

## 다음 단계 (선택적)

1. **점진적 마이그레이션**: 
   - 환경변수로 새 구조 활성화하여 테스트
   - 안정화 후 기본값을 새 구조로 변경

2. **벡터 인덱스 추가**:
   - 현재는 키워드 기반 필터링
   - Chroma/FAISS 등으로 semantic search 추가 가능

3. **미국 매크로 API**:
   - FRED/연준 REST 클라이언트 추가
   - `us_macro_quarterly.jsonl` 파일 생성

4. **세션 관리 개선**:
   - 현재는 기본 세션 관리만 사용
   - 대화 히스토리 기반 컨텍스트 추가 가능

## 주의사항

- **기존 API 스펙 유지**: 모든 엔드포인트의 입출력 형식은 변경하지 않음
- **하위 호환성**: 기본값은 기존 로직 사용
- **점진적 전환**: 새 구조는 선택적으로 활성화 가능

