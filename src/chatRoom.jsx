import React, { useRef, useState, useEffect } from "react";
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
import profile from './fonts/profile.png';
import { useNavigate} from "react-router-dom";

const mentorData = {
    "피터 린치": {
        title: "피터 린치",
        avatar: peterface,
        backgroundImage: chatBgPeter,
        sendButton: send1,
        intro: "안녕 나는 피터 린치! 일상 속에서 투자할 종목을 찾아내지!",
        followUp: "오늘의 뉴스를 분석해볼까?",
        bubbleColor: "#EAF2FD",
        themeColor: "#2580DE",
    },
    "워렌 버핏": {
        title: "워렌 버핏",
        avatar: buffettface,
        backgroundImage: chatBgBuff,
        sendButton: send2,
        intro: "안녕하세요, 워렌 버핏입니다. 장기적인 관점이 가장 중요하죠.",
        followUp: "오늘의 뉴스를 함께 분석해볼까요?",
        bubbleColor: "#e8ffb7ff",
        themeColor: "#729f10ff",
    },
    "캐시 우드": {
        title: "캐시 우드",
        avatar: woodface,
        backgroundImage: chatBgCathie,
        sendButton: send3,
        intro: "안녕하세요, 캐시 우드입니다. 혁신이야말로 미래의 성장 동력이죠.",
        followUp: "오늘의 기술 뉴스, 함께 보실래요?",
        bubbleColor: "#F3E8FD",
        themeColor: "#9B59B6",
    },
    };

const ChatRoom = ({ onOpenMenu }) => {
  // ✅ mentorData 정의는 이 위에 이미 있음
  // (피터 린치, 워렌 버핏, 캐시 우드 각각의 설정 포함)

  // ✅ mentor 기본값 설정
const [mentor, setMentor] = useState("피터 린치");
const navigate = useNavigate();

useEffect(() => {
  const savedMentor = localStorage.getItem("assignedMentor");
  if (savedMentor && mentorData[savedMentor]) {
    setMentor(savedMentor);
  }
}, []); // ✅ 페이지 진입 시 localStorage 값 불러오기


  // ✅ 나머지 상태들
  const [selectedNews, setSelectedNews] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [visibleStep, setVisibleStep] = useState(0);
  const scrollRef = useRef(null);


  // ✅ 멘토 인삿말 단계별 표시
  useEffect(() => {
    const timers = [
      setTimeout(() => setVisibleStep(1), 1500),
      setTimeout(() => setVisibleStep(2), 3000),
    ];
    return () => timers.forEach((t) => clearTimeout(t));
  }, []);

  // ✅ mentor가 잘못된 경우 예외 처리
  if (!mentor || !mentorData[mentor]) return <div>멘토 정보 없음</div>;

  // ✅ mentor 정보 구조분해 할당
  const {
    title,
    avatar,
    backgroundImage,
    sendButton,
    intro,
    followUp,
    bubbleColor,
    themeColor,
  } = mentorData[mentor];


    const viewportWidth = 260;
    const cardWidth = 220;

    const scrollToCard = (direction) => {
        const el = scrollRef.current;
        if (!el) return;
        const next =
        direction === "right"
            ? el.scrollLeft + cardWidth + 33
            : el.scrollLeft - (cardWidth + 33);
        el.scrollTo({ left: next, behavior: "smooth" });
    };

// ✅ 카드 영역 스크롤 상태 저장
const [scrollLeft, setScrollLeft] = useState(0);

// ✅ 스크롤 이벤트에서 현재 위치 저장
useEffect(() => {
  const el = scrollRef.current;
  if (!el) return;
  const onScroll = () => {
    setScrollLeft(el.scrollLeft);
    const idx = Math.round(el.scrollLeft / (cardWidth + 12));
    setActiveIndex(idx);
  };
  el.addEventListener("scroll", onScroll);
  return () => el.removeEventListener("scroll", onScroll);
}, [cardWidth]);

// ✅ selectedNews가 바뀌더라도 이전 스크롤 위치 유지
useEffect(() => {
  const el = scrollRef.current;
  if (el) el.scrollLeft = scrollLeft;
}, [selectedNews]);


    const newsData = [
        {
        title: "첫 번째 카드뉴스",
        summary: "테슬라가 3분기 실적에서 순이익 20% 증가를 기록했습니다.",
        positive: ["전기차 판매 호조", "공급망 안정"],
        negative: ["생산 단가 상승", "환율 불안"],
        comment: "좋은 실적은 성장 신호지만 단기 조정 가능성도 고려해봐야겠어.",
        },
        {
        title: "두 번째 카드뉴스",
        summary: "애플이 새로운 AI 기능을 탑재한 아이폰을 발표했습니다.",
        positive: ["혁신 기술로 브랜드 강화", "고객 충성도 상승"],
        negative: ["가격 인상 우려", "초기 버그 가능성"],
        comment: "기술 혁신은 시장을 이끌지만, 과열된 기대는 늘 위험하지.",
        },
        {
        title: "세 번째 카드뉴스",
        summary: "삼성이 반도체 회복 기대 속 대규모 투자를 발표했습니다.",
        positive: ["생산능력 확대", "산업 회복 기대감"],
        negative: ["단기 수익성 하락 가능성", "과잉 공급 우려"],
        comment: "투자는 미래를 위한 선택이야. 하지만 타이밍도 중요하지.",
        },
    ];

    const handleInputChange = (e) => {
        setInputText(e.target.value);
        e.target.style.height = "auto";
        const newHeight = Math.min(e.target.scrollHeight, 54);
        e.target.style.height = `${newHeight}px`;
    };

const handleSend = () => {
  if (!inputText.trim()) return;
  setMessages((prev) => [...prev, inputText]);
  setInputText("");
};

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

{/* 헤더 */}
        <div style={{ position: "absolute", top: 0, left: 0, width: "100%", zIndex: 2 }}>
            <div style={{ height: 60, background: "#D9D9D9" }} />
            <div
                style={{
                height: 55,
                background: "white",
                boxShadow: "0px 4px 120px rgba(57, 86, 77, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between", // 좌-중-우 배치
                padding: "0 15px",
                }}
            >
                {/* 왼쪽 프로필 */}
                <img
                src={profile}
                alt="profile"
                onClick={() => navigate("/mypage")}
                style={{ width: 25, marginTop:20, cursor: "pointer" }}
                />
                {/* 가운데 타이틀 */}
                <div style={{ color: "#27292E", fontSize: 16, fontWeight: 700 }}>
                {title}
                </div>
                {/* 오른쪽 메뉴 */}
                <img
                src={menu}
                alt="menu"
                onClick={onOpenMenu}
                style={{ width: 25, marginTop:25, cursor: "pointer" }}
                />
            </div>
        </div>

        {/* 채팅 */}
        <div
            style={{
            position: "absolute",
            top: 130,
            left: 0,
            width: "100%",
            height: 740,
            overflowY: "auto",
            paddingBottom: 120,
            boxSizing: "border-box",
            zIndex: 1,
            }}
        >
            <Row withAvatar>
            <LeftBubble style={{ marginTop: 30 }}>{intro}</LeftBubble>
        {/* 1. 카드뉴스는 항상 렌더되게 수정 */}
        {visibleStep >= 2 && (
        <div
            style={{
            marginTop: 15,
            width: 320,
            height: 280,
            background: themeColor,
            borderRadius: 10,
            borderTopLeftRadius: 0,
            padding: 12,
            color: "white",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            boxSizing: "border-box",
            }}
        >
            {/* 카드 뉴스 영역 */}
            <div
            style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
            }}
            >
            <button
                onClick={() => scrollToCard("left")}
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

            {/* ✅ scrollRef와 스크롤 유지 코드 */}
            <div
                ref={scrollRef}
                style={{
                width: viewportWidth,
                height: 240,
                overflowX: "auto",
                display: "flex",
                scrollSnapType: "x mandatory",
                scrollbarWidth: "none",
                }}
            >
                <style>{`div::-webkit-scrollbar { display: none !important; }`}</style>
                {newsData.map((news, i) => (
                <div
                    key={news.title}
                    onClick={() => setSelectedNews(news)} // ✅ 선택만 변경
                    style={{
                    flexShrink: 0,
                    width: cardWidth,
                    height: 240,
                    background: "white",
                    borderRadius: 10,
                    boxShadow: "0px 2px 6px rgba(0,0,0,0.1)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "flex-start",
                    padding: 12,
                    margin: "0 4px",
                    cursor: "pointer",
                    overflow: "visible",
                    }}
                >
                    <div
                    style={{
                        fontSize: 12,
                        fontWeight: 700,
                        marginBottom: 11,
                        textAlign: "center",
                        color: "#444",
                    }}
                    >
                    {news.title}
                    </div>
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
                    <div
                    style={{
                        fontSize: 10,
                        color: "#444",
                        lineHeight: "15px",
                    }}
                    >
                    {news.summary}
                    </div>
                </div>
                ))}
            </div>

            <button
                onClick={() => scrollToCard("right")}
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

            {/* 아래 점 표시 */}
            <div
            style={{
                display: "flex",
                gap: 6,
                justifyContent: "center",
                marginTop: 4,
            }}
            >
            {newsData.map((_, i) => (
                <div
                key={i}
                style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    backgroundColor:
                    activeIndex === i ? "white" : "rgba(255,255,255,0.4)",
                }}
                />
            ))}
            </div>
        </div>
        )}

        {/* ✅ 선택된 뉴스는 별도 렌더 */}
        {selectedNews && (
        <>
            <div
            style={{
                marginTop: 15,
                width: 283,
                background: bubbleColor,
                borderRadius: 10,
                borderTopLeftRadius: 0,
                padding: "10px 14px",
                color: "#222",
                fontSize: 11,
                lineHeight: "18px",
                textAlign: "left",
            }}
            >
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
                <div style={{ fontSize: 10 }}>{selectedNews.summary}</div>
            </div>

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
                    <div style={{ fontWeight: 600, color: "#388E3C" }}>긍정요인</div>
                    {selectedNews.positive.map((p, idx) => (
                    <div key={idx}>• {p}</div>
                    ))}
                </div>
                <div
                    style={{
                    width: 1,
                    backgroundColor: "#E0E0E0",
                    margin: "0 8px",
                    }}
                />
                <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: "#D32F2F" }}>부정요인</div>
                    {selectedNews.negative.map((n, idx) => (
                    <div key={idx}>• {n}</div>
                    ))}
                </div>
                </div>
            </div>
            </div>

            <LeftBubble
            style={{
                marginTop: 12,
                background: bubbleColor,
                maxWidth: 180,
            }}
            >
            “{selectedNews.comment}”
            </LeftBubble>
        </>
        )}

                    </Row>
                    {messages.map((msg, i) => (
            <div
            key={i}
            style={{
                display: "flex",
                justifyContent: "flex-end",
                marginBottom: 8,
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
                }}
            >
                {msg}
            </div>
            </div>
        ))}
        </div>
                </div>

        {/* 입력창 */}
        <div
            style={{
            position: "absolute",
            bottom: 0,
            width: "34%",
            height: 97,
            background: "white",
            borderTopLeftRadius: 27,
            borderTopRightRadius: 27,
            boxShadow: "0px -4px 120px rgba(57, 86, 77, 0.1)",
            zIndex: 2,
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
                fontFamily: "SF Pro, sans-serif",
                color: "#333",
                width: "100%",
                resize: "none",
                lineHeight: "18px",
                maxHeight: "54px",
                overflowY: "auto",
                boxSizing: "border-box",
                scrollbarWidth: "none",
                msOverflowStyle: "none",
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
    );
};

export default ChatRoom;
