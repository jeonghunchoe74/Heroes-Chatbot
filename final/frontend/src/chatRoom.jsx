import React, { useState, useEffect, useRef, useLayoutEffect } from "react";
import "./chatRoom.css";

import peterface from "./fonts/peterface.png";
import woodface from "./fonts/woodface.png";
import buffettface from "./fonts/buffettface.png";
import menu from "./fonts/menu.png";
import send1 from "./fonts/send1.png";
import send2 from "./fonts/send2.png";
import send3 from "./fonts/send3.png";
import chatBgPeter from "./fonts/personchatback_peter.png";
import chatBgBuff from "./fonts/personchatback_buf.png";
import chatBgCathie from "./fonts/personchatback_wood.png";
import profile from "./fonts/profile.png";
import { useNavigate } from "react-router-dom";

const API_BASE = "http://localhost:8000";

// =======================
//   텍스트 유틸리티
// =======================
const decodeHtmlEntities = (text) => {
    if (!text) return text;
    const textarea = document.createElement("textarea");
    textarea.innerHTML = text;
    return textarea.value;
};

const POSITIVE_KEYWORDS = [
    "상승",
    "호재",
    "강세",
    "확대",
    "개선",
    "수요 증가",
    "성장",
    "기회",
    "견조",
    "회복",
    "경쟁력",
    "신규 수주",
    "안정적",
    "장기 투자금 유입"
];

const NEGATIVE_KEYWORDS = [
    "하락",
    "우려",
    "감소",
    "둔화",
    "약세",
    "리스크",
    "부진",
    "악화",
    "적자",
    "규제",
    "압박",
    "모멘텀 둔화",
    "불확실",
];

const shortenSentence = (text, limit = 80) => {
    if (!text) return "";
    const trimmed = text.trim();
    return trimmed.length > limit ? `${trimmed.slice(0, limit).trim()}…` : trimmed;
};

const extractHighlights = (text = "") => {
    const cleaned = (text || "").replace(/\s+/g, " ").trim();
    if (!cleaned) {
        return {
            positive: "긍정 요인을 찾지 못했습니다.",
            negative: "부정 요인을 찾지 못했습니다.",
        };
    }

    const sentences = cleaned.match(/[^.!?]+[.!?]?/g) || [cleaned];

    const findSentence = (keywords) =>
        sentences.find((sentence) => keywords.some((keyword) => sentence.includes(keyword)));

    const positiveSentence = findSentence(POSITIVE_KEYWORDS) || sentences[0];
    const negativeSentence =
        findSentence(NEGATIVE_KEYWORDS) || sentences[sentences.length - 1] || sentences[0];

    return {
        positive: shortenSentence(positiveSentence) || "긍정 요인을 찾지 못했습니다.",
        negative: shortenSentence(negativeSentence) || "부정 요인을 찾지 못했습니다.",
    };
};

const enrichNewsWithHighlights = (news, baseText) => {
    const rawText = baseText || news.summary || news.description || "";
    const text = decodeHtmlEntities(rawText);
    const { positive, negative } = extractHighlights(text);
    return {
        ...news,
        quickPositive: positive,
        quickNegative: negative,
        factorsPositive: [],
        factorsNegative: [],
    };
};

// =======================
//   mentorData
// =======================
const mentorData = {
    "피터 린치": {
        title: "피터 린치",
        avatar: peterface,
        backgroundImage: chatBgPeter,
        sendButton: send1,
        followUp: "오늘의 뉴스를 분석해볼까?",
        bubbleColor: "#EAF2FD",
        themeColor: "#2580DE",
    },
    "워렌 버핏": {
        title: "워렌 버핏",
        avatar: buffettface,
        backgroundImage: chatBgBuff,
        sendButton: send2,
        followUp: "오늘의 뉴스를 함께 분석해볼까요?",
        bubbleColor: "#e8ffb7ff",
        themeColor: "#729f10ff",
    },
    "캐시 우드": {
        title: "캐시 우드",
        avatar: woodface,
        backgroundImage: chatBgCathie,
        sendButton: send3,
        followUp: "오늘의 기술 뉴스, 함께 보실래요?",
        bubbleColor: "#F3E8FD",
        themeColor: "#9B59B6",
    },
    };

    // =======================
    //   ChatRoom Component
    // =======================
    const ChatRoom = ({ onOpenMenu }) => {
    const navigate = useNavigate();

    const [mentor, setMentor] = useState(
        localStorage.getItem("assignedMentor") || "피터 린치"
    );

    // ---------- 백엔드 연동 상태 ----------
    const [sessionId, setSessionId] = useState(null);
    const [introFromApi, setIntroFromApi] = useState("");   // 백엔드 intro
    const [newsData, setNewsData] = useState([]);           // 백엔드 뉴스
    const [loading, setLoading] = useState(false);

    const [messages, setMessages] = useState([]);           // GPT 대화
    const [inputText, setInputText] = useState("");

    const initLoadedRef = useRef(false);
    const introLoadedRef = useRef(false);

    // 카드 슬라이드 관련
    const [selectedNews, setSelectedNews] = useState(null);
    const [activeIndex, setActiveIndex] = useState(0);

    // 한 장 슬라이드 UI 유지
    const cardWidth = 220;

    // 인트로 순차 노출
    const [visibleStep, setVisibleStep] = useState(0);

    // guru_id 매핑
    const guruMap = {
        "워렌 버핏": "buffett",
        "피터 린치": "lynch",
        "캐시 우드": "wood",
    };
    const guru_id = guruMap[mentor];

    // ==========================
    // intro → followUp → card
    // ==========================
    useEffect(() => {
        if (!introFromApi) return;
        if (introLoadedRef.current) return;  // ← 두 번 실행되는 것 방지
        introLoadedRef.current = true;

        const timer1 = setTimeout(() => setVisibleStep(1), 5000);
        const timer2 = setTimeout(() => setVisibleStep(2), 6000);

        return () => {
            clearTimeout(timer1);
            clearTimeout(timer2);
        };
    }, [introFromApi]);


    // ==========================
    // 초기 로딩: intro + 뉴스 요청
    // ==========================
useEffect(() => {
    if (initLoadedRef.current) return;  // 이미 실행됨 → 재호출 방지
    initLoadedRef.current = true;

    const fetchInit = async () => {
        try {
            const res = await fetch(`${API_BASE}/chatbot/init/${guru_id}`);
            const data = await res.json();
            setSessionId(data.session_id || null);
            setIntroFromApi(data.intro || "");
            const normalizedNews = Array.isArray(data.news)
                ? data.news.map((item) => enrichNewsWithHighlights(item))
                : [];
            setNewsData(normalizedNews);
        } catch (err) {
            console.error("초기 데이터 로딩 실패:", err);
        }
    };
    
    fetchInit();
}, []);   // ★ mentor 제거 → 최초 1회만 실행

    // ================================
    // 카드 왼쪽 / 오른쪽 이동
    // ================================
    const handleMove = (direction) => {
        if (newsData.length === 0) return;

        setActiveIndex((prev) => {
        if (direction === "right") return (prev + 1) % newsData.length;
        return (prev - 1 + newsData.length) % newsData.length;
        });
    };

    // ================================
    // 입력창 자동 높이 조절
    // ================================
    const handleInputChange = (e) => {
        setInputText(e.target.value);
        e.target.style.height = "auto";
        e.target.style.height = Math.min(e.target.scrollHeight, 54) + "px";
    };

    // ================================
    // 뉴스 분석하기 → backend analyze
    // ================================
    const analyzeNews = async (news, index) => {
        const payloadContent = [news.title, news.summary || news.description || ""]
            .filter(Boolean)
            .join("\n\n");

        try {
            setLoading(true);

            const res = await fetch(`${API_BASE}/chatbot/analyze/v2`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    guru_id,
                    content: payloadContent,
                }),
            });

            if (!res.ok) {
                throw new Error(`분석 API 호출 실패 (status ${res.status})`);
            }

            const data = await res.json();
            const cleanSummary = (data.summary || "").trim();
            const cleanExpertComment = (data.expert_comment || data.analysis || "").trim();

            const positiveFactors = Array.isArray(data.positive)
                ? data.positive.filter(Boolean)
                : [];
            const negativeFactors = Array.isArray(data.negative)
                ? data.negative.filter(Boolean)
                : [];

            const sanitizedComment = cleanExpertComment.replace(/<[^>]+>/g, "");
            
            // 섹터 및 주식 리스트
            const sector = (data.sector || "").trim();
            const stocks = Array.isArray(data.stocks) ? data.stocks.filter(Boolean) : [];

            setActiveIndex(index);
            setSelectedNews((prev) => {
                const baseNews =
                    prev && prev.title === news.title ? prev : enrichNewsWithHighlights(news);
                return {
                    ...baseNews,
                    generatedSummary: cleanSummary || baseNews.generatedSummary,
                    comment: sanitizedComment || baseNews.comment || "",
                    factorsPositive: positiveFactors,
                    factorsNegative: negativeFactors,
                    quickPositive: positiveFactors[0] || baseNews.quickPositive,
                    quickNegative: negativeFactors[0] || baseNews.quickNegative,
                    sector: sector || baseNews.sector || "",
                    stocks: stocks.length > 0 ? stocks : (baseNews.stocks || []),
                };
            });
        } catch (err) {
            console.error("뉴스 분석 실패:", err);
            setSelectedNews((prev) => {
                const fallbackNews =
                    prev && prev.title === news.title ? prev : enrichNewsWithHighlights(news);
                if (fallbackNews.comment) {
                    return fallbackNews;
                }
                return {
                    ...fallbackNews,
                    comment: "분석 결과를 불러오지 못했습니다.",
                };
            });
        } finally {
            setLoading(false);
        }
    };

    // ================================
    // GPT 대화 메시지 전송
    // ================================
    const handleSend = async () => {
        if (!inputText.trim()) return;

        const userMessage = { role: "user", content: inputText };
        setMessages((prev) => [...prev, userMessage]);
        setInputText("");

        try {
        const res = await fetch(`${API_BASE}/chatbot`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
            message: userMessage.content,
            guru_id,
            session_id: sessionId,
            }),
        });

        const data = await res.json();
        const botMessage = {
            role: "assistant",
            content: data.response || data.text,
        };

        setMessages((prev) => [...prev, botMessage]);
        setSessionId(data.session_id);
        } catch (err) {
        console.error("GPT 대화 전송 실패:", err);
        }
    };

    // ================================
    // 렌더: 헤더
    // ================================
    const { title, avatar, backgroundImage, sendButton, intro, bubbleColor, themeColor } =
        mentorData[mentor];

    const currentNews = newsData[activeIndex] || null;

    const handleSelectNews = (news) => {
        if (!news) return;
        const enriched = enrichNewsWithHighlights(news);
        setSelectedNews(enriched);
    };

    const renderFactorItems = (items, fallbackText, emptyText) => {
        const normalizedItems =
            (items && items.length ? items : fallbackText ? [fallbackText] : []).map((item) =>
                decodeHtmlEntities(item)
            );
        if (!normalizedItems.length) {
            return <div>• {emptyText}</div>;
        }
        return normalizedItems.slice(0, 3).map((item, idx) => (
            <div key={`${item}-${idx}`} style={{ marginTop: idx === 0 ? 0 : 2 }}>
                • {item}
            </div>
        ));
    };

        // ================================
    // 재사용 Row + LeftBubble 컴포넌트
    // ================================
    const Row = ({ children, withAvatar = false }) => (
        <div
        style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            marginTop: withAvatar ? 0 : 10,
            paddingLeft: 10,
            zIndex: 1,
            position: "relative",
        }}
        >
        {withAvatar ? (
            <div
            style={{
                width: 40,
                height: 40,
                background: "white",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
            }}
            >
            <img
                src={avatar}
                alt="avatar"
                style={{
                width: 32,
                borderRadius: "50%",
                objectFit: "cover",
                marginTop: 19,
                }}
            />
            </div>
        ) : (
            <div style={{ width: 40, height: 1, flexShrink: 0 }} />
        )}

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            {children}
        </div>
        </div>
    );

    const LeftBubble = ({ children, style = {} }) => (
        <div
        style={{
            background: "white",
            borderRadius: 10,
            borderTopLeftRadius: 0,
            padding: "8px 12px",
            maxWidth: 250,
            fontSize: 10,
            lineHeight: "18px",
            textAlign: "left",
            display: "inline-block",
            boxSizing: "border-box",
            ...style,
        }}
        >
        {children}
        </div>
    );

    // ================================
    // 렌더 — 최종 전체 UI
    // ================================
    return (
        <div
        style={{
            width: "100vw",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
        }}
        >
        <div
            style={{
            width: 402,
            height: 874,
            position: "relative",
            backgroundImage: `url(${backgroundImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            overflow: "hidden",
            }}
        >
            {/* 배경 흐림 */}
            <div
            style={{
                position: "absolute",
                inset: 0,
                backgroundColor: "rgba(255, 255, 255, 0.46)",
                zIndex: 0,
            }}
            />

            {/* -------------------------- */}
            {/* 헤더 영역 */}
            {/* -------------------------- */}
            <div style={{ position: "absolute", top: 0, width: "100%", zIndex: 2 }}>
            <div style={{ height: 60, background: "#D9D9D9" }} />

            <div
                style={{
                height: 55,
                background: "white",
                boxShadow: "0px 4px 120px rgba(57, 86, 77, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 15px",
                }}
            >
                {/* 왼쪽 프로필 (마이페이지 이동) */}
                <img
                src={profile}
                alt="profile"
                onClick={() => navigate("/mypage")}
                style={{ width: 25, marginTop: 20, cursor: "pointer" }}
                />

                <div style={{ color: "#27292E", fontSize: 16, fontWeight: 700 }}>
                {title}
                </div>

                {/* 메뉴 버튼 */}
                <img
                src={menu}
                alt="menu"
                onClick={onOpenMenu}
                style={{ width: 25, marginTop: 25, cursor: "pointer" }}
                />
            </div>
            </div>

            {/* -------------------------- */}
            {/* 채팅 영역 */}
            {/* -------------------------- */}
            <div
            style={{
                position: "absolute",
                top: 130,
                left: 0,
                width: "100%",
                height: 740,
                overflowY: "auto",
                paddingBottom: 150,
                boxSizing: "border-box",
                zIndex: 1,
                scrollbarWidth: "none",   // Firefox용
                msOverflowStyle: "none",  // IE/Edge용
            }}
            >
            <style>{`div::-webkit-scrollbar { display: none; }`}</style>
            {/* 인삿말 */}
            {introFromApi && (
            <Row withAvatar>
                <LeftBubble style={{ marginTop: 30 }}>
                {introFromApi}
                </LeftBubble>
            </Row>
            )}

            {/* Follow-up 문구 */}
            {introFromApi && visibleStep >= 1 && (
            <Row withAvatar>
                <LeftBubble style={{ marginTop: 10 }}>
                {mentorData[mentor].followUp}
                </LeftBubble>
            </Row>
            )}

            {/* -------------------------- */}
            {/* 카드뉴스 영역 (세번째 단계) */}
            {/* -------------------------- */}
            {visibleStep >= 2 && currentNews && (
                <Row withAvatar>
                <div
                    style={{
                    marginTop: 15,
                    width: 280,
                    height: 260,
                    background: themeColor,
                    borderRadius: 10,
                    borderTopLeftRadius: 0,
                    padding: 12,
                    color: "white",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 10,
                    }}
                >
                    {/* 좌우 버튼 영역 */}
                    <div
                    style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                    }}
                    >
                    {/* <<< 왼쪽 버튼 */}
                    <button
                        onClick={() => handleMove("left")}
                        style={{
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        background: "white",
                        color: themeColor,
                        border: "none",
                        fontSize: 10,
                        cursor: "pointer",
                        }}
                    >
                        ◀
                    </button>

                    {/* 현재 카드 */}
                    <div
                        onClick={() => handleSelectNews(currentNews)}
                        style={{
                        width: cardWidth,
                        height: 240,
                        background: "white",
                        borderRadius: 10,
                        boxShadow: "0px 2px 6px rgba(0,0,0,0.1)",
                        padding: 12,
                        cursor: "pointer",
                        boxSizing: "border-box",
                        display: "flex",
                        flexDirection: "column",
                        }}
                    >
                        {/* 카드 번호 표시 */}
                        <div
                            style={{
                            fontSize: 11,
                            fontWeight: 600,
                            color: "#777",
                            marginBottom: 5,
                            textAlign: "center",
                            }}
                        >
                            {`${activeIndex + 1}번째 카드뉴스`}
                        </div>
                        
                        {/* 제목 */}
                        <div
                        style={{
                            fontSize: 12,
                            fontWeight: 700,
                            marginBottom: 11,
                            textAlign: "center",
                            color: "#444",
                        }}
                        >
                        {currentNews.link ? (
                            <a
                                href={currentNews.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                style={{
                                    color: "#444",
                                    textDecoration: "none",
                                    cursor: "pointer",
                                }}
                                onMouseEnter={(e) => {
                                    e.target.style.textDecoration = "underline";
                                    e.target.style.color = "#2580DE";
                                }}
                                onMouseLeave={(e) => {
                                    e.target.style.textDecoration = "none";
                                    e.target.style.color = "#444";
                                }}
                            >
                                {decodeHtmlEntities(currentNews.title)}
                            </a>
                        ) : (
                            decodeHtmlEntities(currentNews.title)
                        )}
                        </div>

                        {/* 이미지 영역 */}
                        <div
                        style={{
                            width: "100%",
                            height: 110,
                            borderRadius: 8,
                            background: "linear-gradient(135deg, #6574CF, #7A44FF)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            marginBottom: 15,
                        }}
                        >
                        <span style={{ fontSize: 24 }}>📰</span>
                        </div>

                        {/* 요약문 */}
                        <div
                        style={{
                            fontSize: 10,
                            color: "#444",
                            lineHeight: "15px",
                            overflowY: "auto",
                        }}
                        >
                        {decodeHtmlEntities(currentNews.summary)}
                        </div>

                        {/* 분석하기 버튼 */}
                        <button
                        onClick={(e) => {
                            e.stopPropagation();
                            analyzeNews(currentNews, activeIndex);
                        }}
                        disabled={loading}
                        style={{
                            marginTop: 6,
                            alignSelf: "flex-start",
                            background: "#E9ECF2",
                            color: "#444",
                            border: "none",
                            borderRadius: 6,
                            padding: "3px 8px",
                            cursor: "pointer",
                            fontSize: 10,
                        }}
                        >
                        분석하기
                        </button>
                    </div>

                    {/* >>> 오른쪽 버튼 */}
                    <button
                        onClick={() => handleMove("right")}
                        style={{
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        background: "white",
                        color: themeColor,
                        border: "none",
                        fontSize: 10,
                        cursor: "pointer",
                        }}
                    >
                        ▶
                    </button>
                    </div>

                    {/* 아래 점 3개 */}
                    <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                    {newsData.map((_, i) => (
                        <div
                        key={i}
                        style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            backgroundColor:
                            activeIndex === i
                                ? "white"
                                : "rgba(255,255,255,0.4)",
                        }}
                        />
                    ))}
                    </div>
                </div>
                </Row>
            )}

            {/* -------------------------- */}
            {/* 선택된 뉴스 상세 분석 패널 */}
            {/* -------------------------- */}
            {selectedNews && (
                <Row withAvatar>
                <>
                    <div
                    style={{
                        marginTop: 15,
                        marginBottom:15,
                        width: 283,
                        background: bubbleColor,
                        borderRadius: 10,
                        borderTopLeftRadius: 0,
                        padding: "10px 14px",
                        color: "#222",
                        fontSize: 11,
                        lineHeight: "18px",
                    }}
                    >
                    {/* 설명 */}
                    <div
                        style={{
                        background: "white",
                        borderRadius: 6,
                        padding: 8,
                        marginBottom: 10,
                        border: "1px solid #C5D8F1",
                        }}
                    >
                        <div
                        style={{
                            fontWeight: 700,
                            color: themeColor,
                            marginBottom: 8,
                        }}
                        >
                        📝 설명
                        </div>

                        <div style={{ fontSize: 10 }}>
                        {decodeHtmlEntities(
                            selectedNews.generatedSummary || selectedNews.summary
                        )}
                        </div>
                    </div>

                    {/* 영향 분석 placeholder (positive/negative 리스트 유지) */}
                    <div
                        style={{
                        background: "white",
                        borderRadius: 6,
                        padding: 8,
                        border: "1px solid #C5D8F1",
                        }}
                    >
                        <div
                        style={{
                            fontWeight: 700,
                            color: themeColor,
                            marginBottom: 8,
                        }}
                        >
                        📊 영향분석
                        </div>

                        <div style={{ display: "flex", fontSize: 10 }}>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 600, color: "#388E3C" }}>
                            긍정요인
                            </div>
                            <div style={{ marginTop: 4, color: "#666", whiteSpace: "pre-line" }}>
                            {renderFactorItems(
                                selectedNews.factorsPositive,
                                selectedNews.quickPositive,
                                "긍정 요인을 찾는 중입니다."
                            )}
                            </div>
                        </div>

                        <div
                            style={{
                            width: 1,
                            backgroundColor: "#E0E0E0",
                            margin: "0 8px",
                            }}
                        />

                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 600, color: "#D32F2F" }}>
                            부정요인
                            </div>
                            <div style={{ marginTop: 4, color: "#666", whiteSpace: "pre-line" }}>
                            {renderFactorItems(
                                selectedNews.factorsNegative,
                                selectedNews.quickNegative,
                                "부정 요인을 찾는 중입니다."
                            )}
                            </div>
                        </div>
                        </div>
                    </div>
                    </div>

                    {/* 분석 결과 말풍선(comment) */}
                    {selectedNews.comment && (
                    <LeftBubble
                        style={{
                        marginBottom: 10,
                        background: bubbleColor,
                        maxWidth: 310,
                        whiteSpace: "pre-line",
                        }}
                    >
                        {decodeHtmlEntities(selectedNews.comment)}
                    </LeftBubble>
                    )}

                    {/* 섹터 및 주식 리스트 말풍선 */}
                    {selectedNews.sector && selectedNews.stocks && selectedNews.stocks.length > 0 && (
                    <LeftBubble
                        style={{
                        marginBottom: 10,
                        background: bubbleColor,
                        maxWidth: 310,
                        padding: "12px 14px",
                        }}
                    >
                        <div style={{ fontWeight: 700, color: themeColor, marginBottom: 8, fontSize: 12 }}>
                            📊 {selectedNews.sector}
                        </div>
                        <div style={{ fontSize: 11, color: "#444", lineHeight: "18px" }}>
                            <div style={{ fontWeight: 600, marginBottom: 6, color: "#666" }}>
                                관련 종목 (시총 상위 5개)
                            </div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                {selectedNews.stocks.map((stock, idx) => (
                                    <span
                                        key={idx}
                                        style={{
                                            background: "white",
                                            padding: "4px 8px",
                                            borderRadius: 6,
                                            fontSize: 10,
                                            border: `1px solid ${themeColor}`,
                                            color: themeColor,
                                        }}
                                    >
                                        {stock}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </LeftBubble>
                    )}
                </>
                </Row>
            )}

            {/* -------------------------- */}
            {/* GPT 대화 메시지 */}
            {/* -------------------------- */}
            {messages.map((msg, i) => {
            // 유저 메시지
            if (msg.role === "user") {
                return (
                <div
                    key={i}
                    style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    marginBottom: 10,
                    marginRight: 10,
                    }}
                >
                    <div
                    style={{
                        background: "#fbeb56ff",
                        borderRadius: 10,
                        borderTopRightRadius: 0,
                        padding: "8px 12px",
                        fontSize: 11,
                        lineHeight: "18px",
                        maxWidth: 240,
                        whiteSpace: "pre-line",
                    }}
                    >
                    {msg.content}
                    </div>
                </div>
                );
            }

            // 어시스턴트(멘토) 메시지 → 아바타 + 왼쪽 말풍선
            return (
                <Row withAvatar key={i}>
                <LeftBubble style={{ background: "#ffffff", marginBottom:10 }}>
                    {msg.content}
                </LeftBubble>
                </Row>
            );
            })}

            </div>

            {/* -------------------------- */}
            {/* 입력창 */}
            {/* -------------------------- */}
            <div
            style={{
                position: "absolute",
                bottom: 0,
                width: "100%",
                height: 97,
                background: "white",
                borderTopLeftRadius: 27,
                borderTopRightRadius: 27,
                boxShadow: "0px -4px 120px rgba(57, 86, 77, 0.1)",
                zIndex: 5,
            }}
            >
            <div
                style={{
                width: 330,
                height: 36,
                position: "absolute",
                left: "50%",
                transform: "translateX(-50%)",
                bottom: 45,
                background: "#F2F2F2",
                borderRadius: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingLeft: 20,
                paddingRight: 20,
                }}
            >
                <textarea
                placeholder="입력..."
                value={inputText}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                    }
                }}
                style={{
                    border: "none",
                    outline: "none",
                    background: "transparent",
                    fontSize: 13,
                    fontFamily: "SF Pro, Apple SD Gothic Neo, sans-serif",
                    width: "100%",
                    resize: "none",
                    lineHeight: "18px",
                    maxHeight: "54px",
                    overflowY: "auto",
                    paddingTop: 20,
                }}
                />

                <img
                src={sendButton}
                alt="send"
                onClick={handleSend}
                style={{ width: 18, marginTop: 22, cursor: "pointer" }}
                />
            </div>
            </div>
        </div>
        </div>
    );
};

export default ChatRoom;
