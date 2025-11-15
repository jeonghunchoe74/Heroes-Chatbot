# app/services/langchain_rag.py
"""
LangChain 기반 RAG 파이프라인

구성 요소:
- BM25 retriever (멘토별)
- Stuff documents chain (draft answer 생성)
- Validator chain (JSON 출력, 검증 결과 포함)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.retrievers import BM25Retriever

# LangChain 1.0에서는 create_stuff_documents_chain이 다른 위치에 있거나
# 직접 구현해야 할 수 있습니다. 대안으로 RunnablePassthrough를 사용합니다.
try:
    from langchain.chains.combine_documents import create_stuff_documents_chain
    _HAS_STUFF_CHAIN = True
except ImportError:
    # LangChain 1.0 대안: 직접 구현
    from langchain_core.runnables import RunnableLambda
    _HAS_STUFF_CHAIN = False
    
    def create_stuff_documents_chain(llm, prompt):
        """LangChain 1.0 호환: stuff documents chain 직접 구현"""
        def format_and_invoke(input_dict: Dict[str, Any]) -> str:
            docs = input_dict.get("context", [])
            query = input_dict.get("input", "")
            guru_name = input_dict.get("guru_name", "")
            
            # 문서를 텍스트로 변환
            if isinstance(docs, list):
                context_text = "\n\n".join(doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in docs)
            else:
                context_text = str(docs)
            
            # 프롬프트에 변수 전달
            formatted_prompt = prompt.format_messages(
                context=context_text,
                input=query,
                guru_name=guru_name
            )
            
            # LLM 호출 (동기 방식이므로 여기서는 비동기 처리가 필요)
            # 실제로는 이 함수가 async가 아니므로 다른 방식 필요
            return {"formatted_context": context_text, "input": query, "guru_name": guru_name}
        
        # RunnablePassthrough를 사용하여 입력을 그대로 전달하고,
        # format_and_invoke에서 처리한 후 prompt와 llm을 연결
        return (
            RunnableLambda(lambda x: {
                "context": "\n\n".join(doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in x.get("context", [])),
                "input": x.get("input", ""),
                "guru_name": x.get("guru_name", "")
            })
            | prompt
            | llm
        )

from app.services.llm_service import _get_chat_openai
from app.services.rag_service import (
    get_guru_philosophy_snippets,
    initialize_rag_cache,
)
from app.mentors.types import Intent, MentorId
from app.utils.mentor_utils import normalize_mentor_id

logger = logging.getLogger(__name__)

# 전역 retriever 캐시 (멘토별)
_retriever_cache: Dict[str, BM25Retriever] = {}


def _build_retriever(guru_id: MentorId) -> BM25Retriever:
    """
    멘토별 BM25 retriever 생성 및 캐싱.
    
    Args:
        guru_id: 멘토 ID
        
    Returns:
        BM25Retriever 인스턴스
        
    Raises:
        ImportError: rank_bm25가 설치되지 않은 경우
    """
    normalized_id = normalize_mentor_id(guru_id)
    
    if normalized_id in _retriever_cache:
        return _retriever_cache[normalized_id]
    
    # rank_bm25 설치 확인
    try:
        import rank_bm25
    except ImportError:
        raise ImportError(
            "rank_bm25 모듈이 설치되지 않았습니다. "
            "다음 명령어로 설치하세요: pip install rank-bm25"
        )
    
    # RAG 캐시 초기화
    initialize_rag_cache()
    
    # Philosophy 데이터를 Document로 변환
    # 모든 스니펫을 가져오기 위해 top_k를 크게 설정
    philosophy_snippets = get_guru_philosophy_snippets(
        normalized_id,
        intent=None,
        query="",
        top_k=10000,  # 충분히 큰 값으로 모든 스니펫 가져오기
    )
    
    documents = []
    for snippet in philosophy_snippets:
        content = snippet.get("page_content") or snippet.get("text") or snippet.get("content") or ""
        if not content:
            continue
        
        metadata = snippet.get("metadata", {})
        documents.append(Document(page_content=content, metadata=metadata))
    
    if not documents:
        logger.warning(f"No documents found for {normalized_id}, creating empty retriever")
        # 빈 retriever 생성 (최소한 빈 리스트라도 반환하도록)
        retriever = BM25Retriever.from_documents([Document(page_content="", metadata={})])
        _retriever_cache[normalized_id] = retriever
        return retriever
    
    # BM25 retriever 생성
    retriever = BM25Retriever.from_documents(documents)
    retriever.k = 5  # 기본 top_k
    
    _retriever_cache[normalized_id] = retriever
    logger.info(f"Built BM25 retriever for {normalized_id} with {len(documents)} documents")
    
    return retriever


def _create_rag_chain(guru_id: MentorId) -> Any:
    """
    Stuff documents chain 생성 (draft answer 생성용).
    
    Args:
        guru_id: 멘토 ID
        
    Returns:
        Runnable chain
    """
    llm = _get_chat_openai(model_kind="mentor", guru_id=guru_id)
    
    # RAG 프롬프트 템플릿
    if _HAS_STUFF_CHAIN:
        # 원래 create_stuff_documents_chain 사용 시
        prompt = ChatPromptTemplate.from_messages([
            ("system", """너는 투자 멘토의 투자 철학을 바탕으로 답변하는 AI 어시스턴트다.

아래에 제공된 문서들을 참고하여 사용자의 질문에 답변하라.

중요:
- 제공된 문서의 내용만 사용하라.
- 문서에 없는 내용은 추측하지 말라.
- 문서의 내용을 그대로 인용하거나 요약하라.
- 답변은 자연스럽고 친절한 톤으로 작성하라.

문서:
{context}

사용자 질문: {input}"""),
            ("human", "{input}"),
        ])
        rag_chain = create_stuff_documents_chain(llm, prompt)
    else:
        # 대안 구현 사용 시
        prompt = ChatPromptTemplate.from_messages([
            ("system", """너는 {guru_name}의 투자 철학을 바탕으로 답변하는 AI 어시스턴트다.

아래에 제공된 문서들을 참고하여 사용자의 질문에 답변하라.

중요:
- 제공된 문서의 내용만 사용하라.
- 문서에 없는 내용은 추측하지 말라.
- 문서의 내용을 그대로 인용하거나 요약하라.
- 답변은 자연스럽고 친절한 톤으로 작성하라.

문서:
{context}

사용자 질문: {input}"""),
            ("human", "{input}"),
        ])
        rag_chain = create_stuff_documents_chain(llm, prompt)
    
    return rag_chain


def _create_validator_chain(guru_id: MentorId) -> Any:
    """
    Validator chain 생성 (JSON 출력, 검증 결과 포함).
    
    Args:
        guru_id: 멘토 ID
        
    Returns:
        Runnable chain
    """
    llm = _get_chat_openai(model_kind="mentor", guru_id=guru_id)
    
    # Validator 프롬프트
    validator_prompt = ChatPromptTemplate.from_messages([
        ("system", """너는 RAG 응답 검증자다.

다음 draft answer를 검증하고, JSON 형식으로 결과를 반환하라.

출력 형식 (반드시 JSON만):
{{
    "is_valid": true/false,
    "final_answer": "검증된 최종 답변 (개선된 버전)",
    "confidence": 0.0-1.0,
    "issues": ["문제점1", "문제점2"] 또는 []
}}

검증 기준:
1. 답변이 질문에 적절히 답하는가?
2. 답변이 제공된 문서 내용과 일치하는가?
3. 답변이 명확하고 이해하기 쉬운가?
4. 답변에 추측이나 문서에 없는 내용이 포함되어 있지 않은가?

is_valid가 false인 경우:
- issues에 구체적인 문제점을 나열하라.
- final_answer에는 문제점을 수정한 개선된 답변을 제공하라.

is_valid가 true인 경우:
- final_answer는 draft_answer를 그대로 사용하거나 약간 개선할 수 있다.
- issues는 빈 배열 []로 설정하라.

중요: 반드시 유효한 JSON만 출력하라. JSON 이외의 텍스트는 포함하지 말라."""),
        ("human", """질문: {query}

Draft Answer:
{draft_answer}

검증 결과를 JSON 형식으로 반환하라:"""),
    ])
    
    # JSON 파서
    json_parser = JsonOutputParser()
    
    # Chain 구성
    validator_chain = validator_prompt | llm | json_parser
    
    return validator_chain


async def run_rag_pipeline(
    query: str,
    guru_id: MentorId,
    intent: Optional[Intent] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    RAG 파이프라인 실행: retriever → rag_chain → validator_chain
    
    Args:
        query: 사용자 질문
        guru_id: 멘토 ID
        intent: Intent (선택적, 필터링용)
        top_k: 검색할 문서 개수
        
    Returns:
        {
            "docs": List[Document],
            "draft_answer": str,
            "validated_answer": str,
            "is_valid": bool,
            "confidence": float,
            "issues": List[str],
        }
    """
    normalized_id = normalize_mentor_id(guru_id)
    
    # 1. Retriever로 관련 문서 검색
    try:
        retriever = _build_retriever(normalized_id)
        retriever.k = top_k
        docs = retriever.invoke(query)
    except ImportError as exc:
        # rank_bm25가 설치되지 않은 경우: 레거시 RAG 서비스로 fallback
        logger.warning(f"BM25Retriever not available ({exc}), falling back to legacy RAG service")
        philosophy_snippets = get_guru_philosophy_snippets(
            normalized_id,
            intent=intent,
            query=query,
            top_k=top_k,
        )
        # Document로 변환
        docs = []
        for snippet in philosophy_snippets:
            content = snippet.get("page_content") or snippet.get("text") or snippet.get("content") or ""
            if content:
                metadata = snippet.get("metadata", {})
                docs.append(Document(page_content=content, metadata=metadata))
        logger.info(f"Fallback: Using {len(docs)} snippets from legacy RAG service")
    except Exception as exc:
        logger.error(f"Retriever failed: {exc}", exc_info=True)
        docs = []
    
    # 문서가 없으면 빈 결과 반환
    if not docs:
        logger.warning(f"No documents retrieved for query: {query}")
        return {
            "docs": [],
            "draft_answer": "",
            "validated_answer": "죄송합니다. 관련 정보를 찾을 수 없습니다.",
            "is_valid": False,
            "confidence": 0.0,
            "issues": ["관련 문서를 찾을 수 없습니다."],
        }
    
    # 2. RAG chain으로 draft answer 생성
    rag_chain = _create_rag_chain(normalized_id)
    
    try:
        # 멘토 이름 매핑
        guru_names = {
            "buffett": "워렌 버핏",
            "lynch": "피터 린치",
            "wood": "캐시 우드",
        }
        guru_name = guru_names.get(normalized_id, normalized_id)
        
        if _HAS_STUFF_CHAIN:
            # 원래 create_stuff_documents_chain 사용
            draft_answer = await rag_chain.ainvoke({
                "input": query,
                "context": docs,
            })
        else:
            # 대안 구현 사용 (Document 리스트를 그대로 전달)
            result = await rag_chain.ainvoke({
                "input": query,
                "context": docs,
                "guru_name": guru_name,
            })
            # LLM 응답에서 content 추출
            if hasattr(result, 'content'):
                draft_answer = result.content
            elif isinstance(result, str):
                draft_answer = result
            else:
                draft_answer = str(result)
    except Exception as exc:
        logger.error(f"RAG chain failed: {exc}", exc_info=True)
        draft_answer = "죄송합니다. 답변 생성 중 오류가 발생했습니다."
    
    # 3. Validator chain으로 검증
    validator_chain = _create_validator_chain(normalized_id)
    
    try:
        validation_result = await validator_chain.ainvoke({
            "query": query,
            "draft_answer": draft_answer,
        })
        
        # JSON 파싱 결과 처리
        if isinstance(validation_result, dict):
            is_valid = validation_result.get("is_valid", False)
            validated_answer = validation_result.get("final_answer", draft_answer)
            confidence = validation_result.get("confidence", 0.5)
            issues = validation_result.get("issues", [])
        else:
            # 파싱 실패 시 기본값
            logger.warning(f"Validator returned non-dict: {type(validation_result)}")
            is_valid = True
            validated_answer = draft_answer
            confidence = 0.7
            issues = []
    except Exception as exc:
        logger.error(f"Validator chain failed: {exc}", exc_info=True)
        # 검증 실패 시 draft answer 사용
        is_valid = True
        validated_answer = draft_answer
        confidence = 0.5
        issues = ["검증 과정에서 오류가 발생했습니다."]
    
    logger.info(
        f"[RAG_PIPELINE] Query: {query[:50]}..., "
        f"Docs: {len(docs)}, Valid: {is_valid}, Confidence: {confidence}"
    )
    
    return {
        "docs": docs,
        "draft_answer": draft_answer,
        "validated_answer": validated_answer,
        "is_valid": is_valid,
        "confidence": confidence,
        "issues": issues,
    }

