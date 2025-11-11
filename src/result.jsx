import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./result.css";
import cloud1 from "./fonts/Cloud1.png";
import peter from "./fonts/peter.png";
import cathie from "./fonts/cathie.png";
import buffett from "./fonts/buffett.png";

const mentorData = {
    "피터 린치": {
        image: peter,
        type: "생활 밀착형",
        desc: "주변에서 발견하는 기회를 놓치지 않는다",
        cardBorder: "#000000",
        cardBg: "#ffffff",
        buttonBg: "#2580DE",
        descBg: "#E6F4FF",
    },
    "워렌 버핏": {
        image: buffett,
        type: "가치 투자형",
        desc: "10년간 주식을 소유할 생각이 없다면 10분도 갖고 있지 말라",
        cardBorder: "#000000",
        cardBg: "#ffffff",
        buttonBg: "#9FDD18",
        descBg: "#E5FFE0",
    },
    "캐시 우드": {
        image: cathie,
        type: "혁신 성장형",
        desc: "파괴적 혁신은 시장이 예측하는 것보다 훨씬 더 빠르게 일어난다",
        cardBorder: "#000000",
        cardBg: "#ffffff",
        buttonBg: "#EF5A56",
        descBg: "#FFE0E0",
    },
    };

    const Result = () => {
    const [mentor, setMentor] = useState("");
    const navigate = useNavigate();

    useEffect(() => {
        const savedMentor = localStorage.getItem("assignedMentor");
        if (savedMentor) setMentor(savedMentor);
    }, []);

    if (!mentor) {
        return (
        <div className="mymen-container">
            <img src={cloud1} alt="background" className="mymen-bg" />
        </div>
        );
    }

    const { image, type, desc, cardBorder, cardBg, buttonBg, descBg, chatRoute } =
        mentorData[mentor] || {};

    const handleMovePage = () => {
        navigate("/chat");
    };

    return (
        <div className="mymen-container">
        <img src={cloud1} alt="background" className="mymen-bg" />

        {/* 상단 타이틀 */}
        <div className="mymen-title">당신의 멘토</div>

        {/* 프로필 카드 */}
        <div
            className="mymen-card"
            style={{ border: `1.5px solid ${cardBorder}`, background: cardBg }}
        />

        {/* 멘토 이미지 */}
        {image && <img src={image} alt={mentor} className="mymen-image" />}

        {/* 이름, 유형, 설명 */}
        <div className="mymen-name">{mentor}</div>
        <div className="mymen-type">{type}</div>
        <div className="mymen-desc-box" style={{ backgroundColor: descBg }}>
            <div className="mymen-desc-text">{desc}</div>
        </div>

        {/* 버튼 */}
        <div className="mymen-button" style={{ background: buttonBg }} onClick={handleMovePage}>
            <div className="mymen-button-text">영웅과 멘토링 시작하기</div>
        </div>
        </div>
    );
};

export default Result;
