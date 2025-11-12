import React from "react";
import "./App.css";
import back from "./fonts/back.png";
import buffett from "./fonts/buffett.png";
import cathie from "./fonts/cathie.png";
import peter from "./fonts/peter.png";
import personchatback from "./fonts/personchatback_peter.png";
import { useNavigate } from "react-router-dom";

function ChoosePer() {
    const navigate = useNavigate();

    const mentors = [
        {
        name: "워렌 버핏",
        eng: "Warren Buffett",
        quote: "“좋은 회사를 사서 평생 들고 가라.\n시간이 당신의 편이 되어줄 것이다.”",
        color: "#4db15cff",
        img: buffett,
        styleType: "가치 투자형",
        styleColor: "#c9f4b7ff",
        },
        {
        name: "캐시 우드",
        eng: "Cathie Wood",
        quote: "“두려움이 가장 클 때,\n나는 가장 많이 산다.”",
        color: "#dd5454ff",
        img: cathie,
        styleType: "성장 배팅형",
        styleColor: "#f8c5d7ff",
        },
        {
        name: "피터 린치",
        eng: "Peter Lynch",
        quote: "“주식시장은 일상에서 시작된다.\n당신이 아는 게 최고의 투자 아이디어다.”",
        color: "#656ff0ff",
        img: peter,
        styleType: "생활 밀착형",
        styleColor: "#c3e5f3ff",
        },
    ];

    const handleSelect = (mentorName) => {
    localStorage.setItem("assignedMentor", mentorName); // ✅ 선택 멘토 저장
    navigate("/chat"); // ✅ ChatRoom으로 이동
    };


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
            overflow: "hidden",
            backgroundImage: `url(${personchatback})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            }}
        >
            {/* 오버레이 */}
            <div
            style={{
                position: "absolute",
                inset: 0,
                backgroundColor: "rgba(246, 246, 246, 0.92)",
            }}
            />

            {/* 상단 회색바 */}
            <div
            style={{
                width: 402,
                height: 60,
                position: "absolute",
                top: 0,
                background: "#D9D9D9",
                zIndex: 2,
            }}
            />

            {/* 상단 흰색바 */}
            <div
            style={{
                width: 402,
                height: 55,
                top: 60,
                position: "absolute",
                background: "white",
                boxShadow: "0px 4px 120px rgba(57, 86, 77, 0.15)",
                zIndex: 2,
            }}
            />

            {/* 뒤로가기 */}
            <img
            src={back}
            alt="뒤로가기"
            onClick={() => navigate(-1)}
            style={{
                width: 13,
                height: 10,
                position: "absolute",
                left: 17,
                top: 83,
                cursor: "pointer",
                zIndex: 3,
            }}
            />

            {/* 타이틀 */}
            <div
            style={{
                position: "absolute",
                left: "50%",
                transform: "translateX(-50%)",
                top: 76,
                textAlign: "center",
                color: "#27292E",
                fontSize: 16,
                fontFamily: "SF Pro",
                fontWeight: "700",
                zIndex: 3,
            }}
            >
            영웅 바꾸기
            </div>

            {/* 중앙 타이틀 */}
            <div
            style={{
                width: "100%",
                textAlign: "center",
                top: 150,
                position: "absolute",
                color: "black",
                fontSize: 22,
                fontFamily: "SF Pro",
                fontWeight: 700,
                zIndex: 3,
            }}
            >
            함께 할 영웅을 선택해주세요 !
            </div>

            {/* 멘토 카드 전체 */}
            <div
            style={{
                width: 372,
                left: 15,
                top: 210,
                position: "absolute",
                zIndex: 3,
            }}
            >
            <div
                style={{
                width: 314,
                left: 29,
                top: 27,
                position: "absolute",
                display: "flex",
                flexDirection: "column",
                gap: 25,
                height: "auto",
                }}
            >
                {mentors.map((m) => (
                <div
                    key={m.name}
                    style={{
                    width: 314,
                    height: 170,
                    position: "relative",
                    background: m.color,
                    boxShadow: "0px 4px 4px rgba(0,0,0,0.25)",
                    border: "1px solid black",
                    borderRadius: 8,
                    flexShrink: 0,
                    }}
                >
                    {/* 인물 이미지 */}
                    <img
                    src={m.img}
                    alt={m.name}
                    style={{
                        width: 76,
                        height: 114,
                        position: "absolute",
                        left: 5,
                        top: 14,
                        objectFit: "cover",
                    }}
                    />

                    {/* 내부 회색 네모 (명언 박스) */}
                    <div
                    style={{
                        width: 207,
                        height: 64,
                        left: 82,
                        top: 52,
                        position: "absolute",
                        background: "#D9D9D9",
                        border: "1px solid black",
                    }}
                    />

                    {/* 이름 */}
                    <div
                    style={{
                        left: 82,
                        top: 22,
                        position: "absolute",
                        color: "black",
                        fontSize: 12,
                        fontFamily: "SF Pro",
                        fontWeight: 700,
                    }}
                    >
                    {m.name} ({m.eng})
                    </div>

                    {/* 투자 스타일 */}
                    <div
                    style={{
                        left: 250,
                        top: 24,
                        position: "absolute",
                        color: m.styleColor,
                        fontSize: 9,
                        fontFamily: "SF Pro",
                        fontWeight: 600,
                    }}
                    >
                    {m.styleType}
                    </div>

                    {/* 명언 */}
                    <div
                    style={{
                        left: 105,
                        top: 64,
                        width: 160,
                        position: "absolute",
                        textAlign: "center",
                        color: "black",
                        fontSize: 9.5,
                        fontFamily: "SF Pro",
                        fontWeight: 590,
                        lineHeight: "20px",
                        whiteSpace: "pre-line",
                    }}
                    >
                    {m.quote}
                    </div>

                    {/* 선택하기 버튼 */}
                    <div
                    onClick={() => handleSelect(m.name)}
                    style={{
                        width: 80,
                        left: 120,
                        top: 142,
                        position: "absolute",
                        textAlign: "center",
                        color: "white",
                        borderRadius: "5px",
                        padding: "4px 0",
                        fontSize: 9.5,
                        fontFamily: "SF Pro",
                        fontWeight: 500,
                        cursor: "pointer",
                    }}
                    >
                    선택하기
                    </div>
                </div>
                ))}
            </div>
            </div>
        </div>
        </div>
    );
}

export default ChoosePer;
