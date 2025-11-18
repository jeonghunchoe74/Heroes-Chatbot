import React, { useState, useEffect } from "react";
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
import { useNavigate, useLocation } from "react-router-dom";

// 배포 환경(Vercel)에서는 VITE_API_URL 환경변수로 백엔드(Render) 주소를 주입하고,
// 환경변수가 없으면 Render 기본 URL(heroes-chat.onrender.com)을 사용합니다.
// 로컬 개발 시에는 .env 파일에 VITE_API_URL=http://127.0.0.1:8000을 설정하세요.
const API_BASE =
  import.meta.env.VITE_API_URL || "https://heroes-chat.onrender.com";

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
    //   ChatRoom Component (단체 → 개인 전용)
    // =======================
    const ChatRoom = () => {
    const navigate = useNavigate();
    const location = useLocation();

    // 단체톡에서 넘어온 guruId(lynch, buffett, ark)를 한국어 이름 + 백엔드 guru_id로 변환
    const fromGroupGuruId = location.state?.guruId;
    const guruIdToMentor = {
        lynch: "피터 린치",
        buffett: "워렌 버핏",
        ark: "캐시 우드",
    };

    const mentor =
        guruIdToMentor[fromGroupGuruId] ||
        localStorage.getItem("assignedMentor") ||
        "피터 린치";

    const guruMap = {
        "워렌 버핏": "buffett",
        "피터 린치": "lynch",
        "캐시 우드": "wood", // 단체에서는 ark, 백엔드에서는 wood 사용
    };
    const guru_id = guruMap[mentor];

    // ---------- 백엔드 연동 상태 ----------
    const [sessionId, setSessionId] = useState(null);

    const [messages, setMessages] = useState([]);           // GPT 대화
    const [inputText, setInputText] = useState("");

    // =======================
    //   반응형 스케일링
    // =======================
    const DESIGN_WIDTH = 402;
    const DESIGN_HEIGHT = 874;
    const [scale, setScale] = useState(1);

    useEffect(() => {
        const updateScale = () => {
        if (typeof window === "undefined") {
            setScale(1);
            return;
        }
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        if (!vw || !vh) {
            setScale(1);
            return;
        }
        const scaleX = vw / DESIGN_WIDTH;
        const scaleY = vh / DESIGN_HEIGHT;
        const nextScale = Math.min(scaleX, scaleY);
        setScale(nextScale);
        };

        updateScale();
        window.addEventListener("resize", updateScale);
        return () => window.removeEventListener("resize", updateScale);
    }, []);

    // ================================
    // 입력창 변경
    // ================================
    const handleInputChange = (e) => {
        setInputText(e.target.value);
    };

    // ================================
    // GPT 대화 메시지 전송
    // ================================
    const handleSend = async () => {
        const raw = (inputText || "").trim();
        if (!raw) return;

        // UI에는 사용자가 입력한 원래 문장만 보여줌
        const userMessage = { role: "user", content: raw };
        setMessages((prev) => [...prev, userMessage]);
        setInputText("");

        try {
            const res = await fetch(`${API_BASE}/chatbot`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: raw,
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
    const { title, avatar, backgroundImage, sendButton, bubbleColor } =
        mentorData[mentor];

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
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        boxSizing: "border-box",
        padding: "0 16px",
        overflow: "hidden",
        }}
        >
        <div
            style={{
            width: DESIGN_WIDTH,
            height: DESIGN_HEIGHT,
            position: "relative",
            backgroundImage: `url(${backgroundImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            overflow: "hidden",
            transform: `scale(${scale})`,
            transformOrigin: "center center",
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
                justifyContent: "center",
                position: "relative",
                paddingInline: 16,
                gap: 16,
                }}
            >
                {/* 왼쪽 프로필 (마이페이지 이동) */}
                <img
                src={profile}
                alt="profile"
                onClick={() => navigate("/mypage")}
                style={{
                    position: "absolute",
                    left: 15,
                    top: 15,
                    width: 25,
                    height: 25,
                    cursor: "pointer",
                }}
                />

                <div style={{ color: "#27292E", fontSize: 16, fontWeight: 700 }}>
                {title}
                </div>

                {/* 개인 / 단체 토글 (여기서는 개인 활성) */}
                <div
                style={{
                    position: "absolute",
                    right: 15,
                    top: 15,
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                }}
                >
                <div
                    style={{
                    display: "flex",
                    borderRadius: 999,
                    border: "1px solid #C8BFB0",
                    background: "#E5DCCF",
                    overflow: "hidden",
                    fontSize: 11,
                    }}
                >
                    <button
                    type="button"
                    style={{
                        padding: "3px 10px",
                        border: "none",
                        background: "#D8CBB9",
                        color: "#333",
                        cursor: "default",
                        fontWeight: 600,
                    }}
                    >
                    개인
                    </button>
                    <button
                    type="button"
                    onClick={() => navigate("/group-chat")}
                    style={{
                        padding: "3px 10px",
                        border: "none",
                        background: "#F7F1E8",
                        color: "#333",
                        cursor: "pointer",
                    }}
                    >
                    단체
                    </button>
                </div>
                </div>
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
                    height: "100%",
                    resize: "none",
                    lineHeight: "18px",
                    overflowY: "auto",
                    paddingTop: 25,
                    paddingBottom: 6,
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

