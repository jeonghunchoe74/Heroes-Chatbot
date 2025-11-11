import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMentor } from "./mentorContext";
import "./App.css";
import Cloud2 from "./fonts/Cloud1.png";
import back from "./fonts/back.png";
import buffett from "./fonts/buffett.png";
import cathie from "./fonts/cathie.png";
import peter from "./fonts/peter.png";

function ChooseMen({ onBack, onSelectPeter }) {
    const [openModal, setOpenModal] = useState(null);
    const navigate = useNavigate();
    const { saveMentor, getMentor } = useMentor();

    const mentors = [
        {
        name: "워렌 버핏",
        eng: "Warren Buffett",
        quote: "“좋은 회사를 사서 평생 들고 가라.\n시간이 당신의 편이 되어줄 것이다.”",
        desc: "가치투자의 대가로 불리는 워렌 버핏은 철저한 기업 분석과 장기투자를 중시합니다. 그는 '시장의 소음'에 흔들리지 않고, 좋은 회사를 오랫동안 보유하는 철학으로 세대를 초월한 투자 전략을 제시했습니다.",
        color: "#51b360ff",
        img: buffett,
        },
        {
        name: "캐시 우드",
        eng: "Cathie Wood",
        quote: "“두려움이 가장 클 때,\n나는 가장 많이 산다.”",
        desc: "ARK Invest의 창립자인 캐시 우드는 혁신 기업에 집중 투자하는 성장형 투자자입니다. 인공지능, 로봇, 전기차 등 미래 산업의 잠재력을 믿고, 시장의 불안정 속에서도 과감한 결정을 내립니다.",
        color: "#de5858ff",
        img: cathie,
        },
        {
        name: "피터 린치",
        eng: "Peter Lynch",
        quote: "“주식시장은 일상에서 시작된다.\n당신이 아는 게 최고의 투자 아이디어다.”",
        desc: "피터 린치는 일상 속에서 투자 아이디어를 찾는 생활 밀착형 투자 철학으로 유명합니다. 그는 ‘자신이 이해하는 기업에 투자하라’는 원칙으로 개인 투자자들에게 실질적인 조언을 남겼습니다.",
        color: "#6b74ffff",
        img: peter,
        },
    ];

    const handleSelectMentor = (mentor) => {
        saveMentor("chooseRoomMentor", mentor.name); // ✅ 새로운 키로 저장
        navigate("/choose-room");
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
            background: "white",
            overflow: "hidden",
        }}
        >
        {/* 배경 이미지 */}
        <img
            src={Cloud2}
            alt="background"
            style={{
            width: 402,
            height: 874,
            position: "absolute",
            left: 0,
            top: 0,
            opacity: 0.4,
            objectFit: "cover",
            }}
        />

        {/* 상단 헤더 (RoomChoose와 동일 정렬) */}
        <div
            style={{
            width: 402,
            height: 49,
            top: 62,
            left: 0,
            position: "absolute",
            background: "white",
            borderBottom: "1px solid #BEBEBE",
            borderTop: "1px solid #BEBEBE",
            }}
        />
        {/* 뒤로가기 버튼 */}
        <img
            src={back}
            alt="back"
            onClick={() => {
            if (window.history.length > 1) {
                navigate(-1);
            } else {
                navigate("/home");
            }
            }}
            style={{
            position: "absolute",
            top: 83,
            left: 25,
            height: 8,
            width: "auto",
            cursor: "pointer",
            zIndex: 1000,
            }}
        />
        <div
            style={{
            width: 120,
            top: 76,
            left: 141,
            position: "absolute",
            color: "black",
            fontSize: 16,
            fontFamily: "SF Pro",
            fontWeight: 700,
            textAlign: "center",
            }}
        >
            영웅과 함께
        </div>

        {/* 제목 */}
        <div
            style={{
            left: 41,
            top: 148,
            position: "absolute",
            textAlign: "center",
            color: "black",
            fontSize: 24,
            fontFamily: "SF Pro",
            fontWeight: 700,
            }}
        >
            세 명의 영웅이 기다리고 있어요 !
        </div>

        {/* 부제 */}
        <div
            style={{
            left: 84,
            top: 191,
            position: "absolute",
            textAlign: "center",
            color: "black",
            fontSize: 11,
            fontFamily: "SF Pro",
            fontWeight: 400,
            lineHeight: "15px",
            }}
        >
            각자 다른 길을 걸어온 영웅들이 당신과 함께합니다.
            <br />
            당신의 투자 스타일과 닮은 영웅을 선택해 보세요.
        </div>

        {/* 멘토 카드들 */}
        <div
            style={{
            width: 372,
            height: 565,
            left: 15,
            top: 248,
            position: "absolute",
            }}
        >
            <div
            style={{
                width: 314,
                height: 509,
                left: 29,
                top: 27,
                position: "absolute",
                display: "flex",
                flexDirection: "column",
                gap: 25,
            }}
            >
            {mentors.map((mentor) => (
                <div
                key={mentor.name}
                onClick={() => handleSelectMentor(mentor)} // ✅ 박스 전체 클릭 시 이동
                style={{
                    width: 314,
                    height: 151,
                    position: "relative",
                    background: mentor.color,
                    boxShadow: "0px 4px 4px rgba(0,0,0,0.25)",
                    border: "1px solid black",
                    cursor: "pointer",
                }}
                >
                <img
                    src={mentor.img}
                    alt={mentor.name}
                    style={{
                    width: 76,
                    height: 114,
                    position: "absolute",
                    left: 5,
                    top: 10,
                    objectFit: "cover",
                    }}
                />
                <div
                    style={{
                    width: 207,
                    height: 64,
                    left: 82,
                    top: 44,
                    position: "absolute",
                    background: "#D9D9D9",
                    border: "1px solid black",
                    }}
                />
                <div
                    style={{
                    left: 82,
                    top: 18,
                    position: "absolute",
                    color: "black",
                    fontSize: 12,
                    fontFamily: "SF Pro",
                    fontWeight: 700,
                    }}
                >
                    {mentor.name} ({mentor.eng})
                </div>
                <div
                    style={{
                    left: 105,
                    top: 56,
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
                    {mentor.quote}
                </div>
                {/* 설명 보기 버튼 (박스 클릭과 별개로 동작) */}
                <div
                    onClick={(e) => {
                    e.stopPropagation(); // ✅ 박스 클릭 이벤트 차단
                    setOpenModal(mentor);
                    }}
                    style={{
                    width: 52,
                    left: 128,
                    top: 130,
                    position: "absolute",
                    textAlign: "center",
                    color: "#DFDFDF",
                    fontSize: 9,
                    fontFamily: "SF Pro",
                    fontWeight: 590,
                    cursor: "pointer",
                    }}
                >
                    설명 보기
                </div>
                </div>
            ))}
            </div>
        </div>

        {/* 모달 */}
        {openModal && (
            <div
            style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: 402,
                height: 874,
                background: "rgba(0,0,0,0.47)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                zIndex: 10,
            }}
            >
            <div
                style={{
                width: 310,
                background: "white",
                borderRadius: "12px",
                padding: "25px",
                textAlign: "center",
                border: "1px solid #ccc",
                boxShadow: "0px 4px 10px rgba(0,0,0,0.25)",
                marginTop: "40px",
                }}
            >
                <img
                src={openModal.img}
                alt={openModal.name}
                style={{
                    width: 100,
                    height: 140,
                    borderRadius: "6px",
                    objectFit: "cover",
                    marginBottom: "12px",
                    marginTop: "10px",
                }}
                />
                <div
                style={{
                    fontSize: 17,
                    fontWeight: 700,
                    fontFamily: "SF Pro",
                    marginBottom: "4px",
                }}
                >
                {openModal.name} ({openModal.eng})
                </div>

                <div
                style={{
                    fontSize: 11,
                    color: "#333",
                    lineHeight: "1.6",
                    whiteSpace: "pre-line",
                    marginBottom: "30px",
                    marginTop: "50px",
                }}
                >
                {openModal.desc}
                </div>
                <div
                onClick={() => setOpenModal(null)}
                style={{
                    background: "#2E2E2E",
                    color: "white",
                    padding: "6px 0",
                    borderRadius: "8px",
                    fontSize: 12,
                    cursor: "pointer",
                }}
                >
                닫기
                </div>
            </div>
            </div>
        )}
        </div>
        </div>
    );
}

export default ChooseMen;