# 아키텍처 분석 및 중복 기능 정리

## 현재 구조 분석

### 1. LangChain/LangGraph 오케스트레이션 위치

**`app/services/chatbot_service.py` (1196줄)**
- **LangGraph 사용**: `StateGraph`를 사용한 간단한 워크플로우
  ```python
  workflow = StateGraph(State)
  workflow.add_node("chatbot", _chatbot_step)
  workflow.add_edge(START, "chatbot")
  workflow.add_edge("chatbot", END)
  chat_graph = workflow.compile()
  ```
- **문제점**: 
  - 단순한 START → chatbot → END 구조로, 실제 오케스트레이션은 함수 내부에서 순차적으로 처리
  - LangGraph의 장점(복잡한 워크플로우, 조건부 분기)을 활용하지 못함
  - 새로운 `unified_chatbot_service.py`는 LangGraph를 사용하지 않음

### 2. 중복 기능 분석

#### Intent 감지 중복
1. **`chatbot_service.py`의 `_infer_intent()`** (251-277줄)
   - 레거시 로직
   - 반환값: `"greeting"`, `"news_analysis"`, `"company_query"`, `"principles"` (문자열)

2. **`intent_service.py`의 `detect_intent()`** (74-124줄)
   - 새로운 로직
   - 반환값: `Intent` enum (`SMALLTALK`, `NEWS_ANALYSIS`, `STOCK_ANALYSIS` 등)

3. **`app/mentors/router.py`의 `route_query()`** (18-146줄)
   - 또 다른 Intent 감지 로직
   - 반환값: `RoutedQuery` 객체

**결론**: Intent 감지가 3곳에 중복되어 있음

#### 심볼 추출 중복
1. **`chatbot_service.py`의 `find_symbols()`** (235-250줄)
   - `symbol_resolver.resolve_symbols_from_text()` 사용

2. **`intent_service.py`의 `extract_symbols()`** (127-149줄)
   - 동일한 `symbol_resolver.resolve_symbols_from_text()` 사용

3. **`app/mentors/router.py`의 `route_query()`** (18-146줄)
   - `symbol_resolver.resolve_symbols_from_text()` 사용

**결론**: 심볼 추출은 공통 함수를 사용하지만, 호출하는 곳이 중복됨

#### RAG 로딩 중복
1. **`chatbot_service.py`의 `_load_persona()`** (318-342줄)
   - `rag_loader.load_persona_chunks()` 사용 (레거시)

2. **`chatbot_service.py`의 `_load_cached_context()`** (343-352줄)
   - 레거시 summaries 로딩

3. **`unified_chatbot_service.py`**
   - `rag_service.get_guru_philosophy_snippets()` 사용 (새로운 구조)

**결론**: 레거시 RAG 로더와 새로운 RAG 서비스가 병행 사용 중

#### LLM 호출 중복
1. **`chatbot_service.py`**
   - `ChatOpenAI` 직접 사용 (26줄)
   - LangGraph의 `_chatbot_step()`에서 `llm.invoke()` 호출

2. **`llm_service.py`**
   - `invoke_llm()` 함수 제공
   - `ChatOpenAI` 래핑

3. **`unified_chatbot_service.py`**
   - 멘토 에이전트를 통해 간접 호출

4. **`app/mentors/buffett_agent.py` 등**
   - `llm_service.invoke_llm()` 사용

**결론**: LLM 호출이 여러 레이어에 분산되어 있음

### 3. 파일별 역할 및 라인 수

| 파일 | 라인 수 | 역할 | 상태 |
|------|---------|------|------|
| `chatbot_service.py` | ~1196 | 레거시 메인 로직 + LangGraph 워크플로우 | **리팩터링 필요** |
| `unified_chatbot_service.py` | ~306 | 새로운 Agent + RAG + REST 파이프라인 | ✅ 새로운 구조 |
| `intent_service.py` | ~221 | Intent 감지, 심볼 추출 등 | ✅ 새로운 구조 |
| `app/mentors/router.py` | ~146 | Intent 라우팅 (중복!) | ⚠️ 중복 |
| `agent_service.py` | ~332 | Agent 설정 및 전략 | ✅ 새로운 구조 |
| `llm_service.py` | ~154 | LLM 호출 전담 | ✅ 새로운 구조 |

### 4. 문제점 요약

1. **`chatbot_service.py`가 너무 큼 (1196줄)**
   - 레거시 로직이 대부분 남아있음
   - 새로운 `unified_chatbot_service`로 위임하지만, fallback 시 전체 로직 실행
   - LangGraph를 사용하지만 단순한 구조로 활용도 낮음

2. **Intent 감지 3중복**
   - `chatbot_service._infer_intent()` (레거시)
   - `intent_service.detect_intent()` (새로운)
   - `app/mentors/router.route_query()` (중복)

3. **RAG 로딩 이중 구조**
   - 레거시: `rag_loader.load_persona_chunks()`
   - 새로운: `rag_service.get_guru_philosophy_snippets()`

4. **LangGraph 활용 부족**
   - 현재는 단순한 START → chatbot → END 구조
   - Intent별 분기, RAG 로딩, REST API 호출 등을 노드로 분리하면 더 명확한 오케스트레이션 가능

## 제안: 리팩터링 방향

### 1. `chatbot_service.py` 정리
- **레거시 로직 제거**: `unified_chatbot_service`가 안정화되면 레거시 코드 삭제
- **LangGraph 오케스트레이션으로 전환**: 
  ```
  START → Router → [Intent별 분기] → RAG Loader → REST API → Mentor Agent → END
  ```

### 2. Intent 감지 통합
- `app/mentors/router.py`의 `route_query()`를 단일 진입점으로 사용
- `chatbot_service._infer_intent()` 제거
- `intent_service.detect_intent()`는 내부적으로만 사용

### 3. RAG 로딩 통합
- `rag_loader`는 레거시 호환용으로만 유지
- 모든 새로운 코드는 `rag_service` 사용

### 4. LangGraph 기반 오케스트레이션 설계
```python
# app/services/orchestration_graph.py (새로 생성)
workflow = StateGraph(State)
workflow.add_node("router", route_query_node)
workflow.add_node("rag_loader", load_rag_node)
workflow.add_node("rest_api", call_rest_api_node)
workflow.add_node("mentor_agent", invoke_mentor_agent_node)
workflow.add_conditional_edges("router", route_by_intent)
workflow.add_edge("rag_loader", "mentor_agent")
workflow.add_edge("rest_api", "mentor_agent")
```

