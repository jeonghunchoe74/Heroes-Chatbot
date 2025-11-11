import React, { useState, useRef } from "react";
import { useMentor } from "./mentorContext";
import "./App.css";
import personchatback from "./fonts/manyback.png";
import menu from "./fonts/menu.png";
import send1 from "./fonts/send1.png";
import peterface from "./fonts/peterface.png";


function ManyChat({ onOpenMenu }) {
    const { getMentor } = useMentor();
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState("");
    const [showPopup, setShowPopup] = useState(false);
    const [popupVisible, setPopupVisible] = useState(false);
    const [popupMessages, setPopupMessages] = useState([]);
    const [popupInput, setPopupInput] = useState("");
    const [showQuestion, setShowQuestion] = useState(false);

    const popupRef = useRef(null);
    const startY = useRef(0);
    const currentY = useRef(0);
    const isDragging = useRef(false);
    const mentorName = getMentor("chooseRoomMentor") || "피터 린치";
    const stockName = getMentor("chooseRoomStock") || "삼성전자";

    const mentors = [
        {
        name: "이다후",
        color: "#F7C948",
        message:
            "www.apple.com",
        },
        {
        name: "윤철진",
        color: "#8E7CC3",
        message: "혁신 기술은 단기 변동보다 미래의 성장을 만든다고 믿어.",
        },
        {
        name: "최정훈",
        color: "#4FA3F7",
        message: "일상에서 소비되는 브랜드 속에 투자 기회가 숨어 있지.",
        },
    ];

    const handleSend = () => {
        if (!inputText.trim()) return;
        setMessages([...messages, inputText]);
        setInputText("");
    };

    const openPopup = () => {
        setShowPopup(true);
        setShowQuestion(false);
        setPopupMessages([]);
        setTimeout(() => {
        setPopupVisible(true);
        setTimeout(() => setShowQuestion(true), 800); // 2초 후 피터린치 질문 등장
        }, 10);
    };

    const closePopup = () => {
        setPopupVisible(false);
        setTimeout(() => setShowPopup(false), 300);
    };

    const handlePopupSend = () => {
        if (!popupInput.trim()) return;
        setPopupMessages([...popupMessages, popupInput]);
        setPopupInput("");
    };

    // ---------- Swipe 기능 ----------
    const handleMouseDown = (e) => {
        isDragging.current = true;
        startY.current = e.clientY || e.touches?.[0]?.clientY;
    };

    const handleMouseMove = (e) => {
        if (!isDragging.current || !popupRef.current) return;
        currentY.current = e.clientY || e.touches?.[0]?.clientY;
        const diff = currentY.current - startY.current;
        if (diff > 0) popupRef.current.style.transform = `translateY(${diff}px)`;
    };

    const handleMouseUp = () => {
        if (!isDragging.current || !popupRef.current) return;
        const diff = currentY.current - startY.current;
        isDragging.current = false;
        popupRef.current.style.transition = "transform 0.3s ease-out";
        if (diff > 120) {
        popupRef.current.style.transform = `translateY(100%)`;
        setTimeout(() => {
            setShowPopup(false);
            setPopupVisible(false);
        }, 300);
        } else {
        popupRef.current.style.transform = "translateY(0)";
        setTimeout(() => {
            if (popupRef.current) popupRef.current.style.transition = "";
        }, 300);
        }
    };

    const LeftBubble = ({ children, color, name, showButton, hasImage }) => (
        <div style={{ display: "flex", flexDirection: "column", marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, paddingLeft: 12 }}>
            <div
            style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: color,
                transform: "translateY(3px)",
            }}
            ></div>
            <div style={{ fontWeight: 700, fontSize: 12, color: "#333", marginTop: 2 }}>
            {name}
            </div>
        </div>

        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, paddingLeft: 52 }}>
            <div
            style={{
                background: "white",
                borderRadius: 10,
                borderTopLeftRadius: 0,
                padding: "10px 13px",
                maxWidth: 250,
                fontSize: 11,
                lineHeight: "18px",
                textAlign: "left",
                boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
                transform: "translateY(-4px)",
            }}
            >
            {children}
            {hasImage && (
                <div
                style={{
                    width: "100%",
                    height: 100,
                    borderRadius: 8,
                    overflow: "hidden",
                    marginTop: 8,
                }}
                >
                <img
                    src="https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg"
                    alt="link-preview"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
                </div>
            )}
            </div>
        </div>

        {showButton && (
            <div
            onClick={openPopup}
            style={{
                marginLeft: 52,
                marginTop: 10,
                width: 70,
                height: 28,
                background: "#4FA3F7",
                color: "white",
                borderRadius: 10,
                textAlign: "center",
                lineHeight: "28px",
                fontSize: 11,
                fontWeight: "600",
                cursor: "pointer",
                boxShadow: "0px 3px 8px rgba(0,0,0,0.15)",
            }}
            >
            분석하기
            </div>
        )}
        </div>
    );

    return (
        <div
        style={{
            width: "100vw",
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-start",
        }}
        >
        <div
        style={{
            width: 402,
            height: 874,
            position: "relative",
            backgroundImage: `url(${personchatback})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            overflow: "hidden",
        }}
        >
        <div style={{ position: "absolute", inset: 0, backgroundColor: "rgba(217, 217, 217, 0.8)" }} />

        {/* 상단 헤더 */}
        <div style={{ position: "absolute", top: 0, left: 0, width: "100%", zIndex: 2 }}>
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
            }}
            >
            <img
                src={menu}
                alt="menu"
                onClick={onOpenMenu}
                style={{ position: "absolute", left: 15, top: 15, width: 25, height: 25, cursor: "pointer" }}
            />
            <div style={{ color: "#27292E", fontSize: 16, fontWeight: 700 }}>
                {stockName} with {mentorName}
            </div>
            </div>
        </div>

        {/* 대화 영역 */}
        <div
            style={{
            position: "absolute",
            top: 130,
            left: 0,
            width: "100%",
            height: 740,
            overflowY: "auto",
            paddingBottom: 120,
            }}
        >
            {mentors.map((mentor, index) => (
            <LeftBubble
                key={index}
                color={mentor.color}
                name={mentor.name}
                showButton={index === 0}
                hasImage={mentor.message.includes("www.")}
            >
                {mentor.message}
            </LeftBubble>
            ))}

            {messages.map((msg, index) => (
            <div key={index} style={{ display: "flex", justifyContent: "flex-end", marginTop: 10, paddingRight: 14 }}>
                <div
                style={{
                    background: "#fbeb56ff",
                    borderRadius: 10,
                    borderTopRightRadius: 0,
                    padding: "8px 12px",
                    maxWidth: 250,
                    fontSize: 10,
                    lineHeight: "18px",
                }}
                >
                {msg}
                </div>
            </div>
            ))}
        </div>

        {/* 하단 입력창 */}
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
            }}
        >
            <div
            style={{
                width: 320,
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
            <input
                type="text"
                placeholder="입력..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                style={{
                border: "none",
                outline: "none",
                background: "transparent",
                fontSize: 13,
                color: "#333",
                width: "100%",
                }}
            />
            <img src={send1} alt="send" onClick={handleSend} style={{ width: 18, height: 18, cursor: "pointer" }} />
            </div>
        </div>

        {/* 팝업 */}
        {showPopup && (
            <>
            <div
                onClick={closePopup}
                style={{
                position: "absolute",
                inset: 0,
                background: "rgba(0,0,0,0.3)",
                zIndex: 3,
                }}
            />

            <div
                ref={popupRef}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onTouchStart={handleMouseDown}
                onTouchMove={handleMouseMove}
                onTouchEnd={handleMouseUp}
                style={{
                position: "absolute",
                left: 0,
                bottom: 0,
                width: "100%",
                height: 760,
                background: "#f1f9ffff",
                borderTopLeftRadius: 25,
                borderTopRightRadius: 25,
                zIndex: 4,
                padding: "16px 24px 100px 24px",
                boxSizing: "border-box",
                transform: popupVisible ? "translateY(0%)" : "translateY(100%)",
                transition: "transform 0.3s ease-out",
                display: "flex",
                flexDirection: "column",
                }}
            >
                <div
                style={{
                    width: 60,
                    height: 4,
                    borderRadius: 3,
                    background: "#ccc",
                    margin: "0 auto 12px",
                }}
                />

                <div
                style={{
                    width: "100%",
                    height: 200,
                    background: "#E0E0E0",
                    borderRadius: 12,
                    marginBottom: 20,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 600,
                    color: "#555",
                    fontSize: 14,
                    marginTop:10,
                }}
                >
                뉴스
                </div>

                <div style={{ flex: 1, overflowY: "auto" }}>
                {/* ✅ 피터 린치 말풍선 */}
                {showQuestion && (
                    <div style={{ display: "flex", flexDirection: "column", marginTop: 10 }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                        <div
    style={{
        width: 32,
        height: 32,
        borderRadius: "50%",
        overflow: "hidden", // 이미지를 원 안에 잘라 넣기
        transform: "translateY(3px)",
        background: '#5353b0ff',
    }}
    >
    <img
        src={peterface}
        alt="peter"
        style={{
        width: "100%",
        height: "100%",
        objectFit: "cover",
        }}
    />
    </div>

                        <div style={{ fontWeight: 700, fontSize: 12, color: "#333", marginTop: 2 }}>
                        피터 린치
                        </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8, paddingLeft: 40 }}>
                        <div
                        style={{
                            background: "#F9F9F9",
                            borderRadius: 10,
                            borderTopLeftRadius: 0,
                            padding: "10px 13px",
                            maxWidth: 250,
                            fontSize: 12,
                            lineHeight: "18px",
                            textAlign: "left", // ✅ 왼쪽 정렬 추가
                            boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
                            transform: "translateY(-4px)",
                        }}
                        >
                        최근 이 뉴스에 대해 어떻게 생각하나?  
                        향후 시장에 어떤 영향을 줄 것 같지?
                        </div>
                    </div>
                    </div>
                )}

                {/* 내가 입력한 메시지 */}
                {popupMessages.map((msg, i) => (
                    <div
                    key={i}
                    style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        marginBottom: 8,
                        marginRight: 10,
                        marginTop: 10,
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

                {/* 입력창 */}
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
            display:'felx',
            justifyContent:"center",
            alignItems:'center',
            transform: 'translateX(-6%)',
            }}
        >
            
        </div>
                <div
                style={{
                    position: "absolute",
                    bottom: 45,
                    left: "50%",
                    transform: "translateX(-50%)",
                    width: 320,
                    height: 36,
                    background: "#F2F2F2",
                    borderRadius: 32,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingLeft: 20,
                    paddingRight: 20,
                }}
                >
                <input
                    type="text"
                    placeholder="답변 입력..."
                    value={popupInput}
                    onChange={(e) => setPopupInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handlePopupSend()}
                    style={{
                    border: "none",
                    outline: "none",
                    background: "transparent",
                    fontSize: 13,
                    color: "#333",
                    width: "100%",
                    }}
                />
                <img src={send1} alt="send" onClick={handlePopupSend} style={{ width: 18, height: 18, cursor: "pointer" }} />
                </div>
            </div>
            </>
        )}
        </div>
        </div>
    );
}

export default ManyChat;
