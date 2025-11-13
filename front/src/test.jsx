import React, { useState } from "react";
import "./test.css";
import { useMentor } from "./mentorContext";
import { useNavigate } from "react-router-dom";
import cloud1 from "./fonts/Cloud1.png";

const Test = () => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [answers, setAnswers] = useState([]);
    const { setMentor } = useMentor();
    const navigate = useNavigate();

    const questions = [
        {
        id: 1,
        question: "내가 투자를 하고 싶은 이유는?",
        options: [
            "A. 안정적으로 노후나 미래를 준비하고 싶다.",
            "B. 세상을 바꿀만한 새로운 산업·기술에 내 돈을 싣고 싶다.",
            "C. 내가 잘 아는 브랜드나 제품으로 재미있게 투자해보고 싶다.",
        ],
        },
        {
        id: 2,
        question: "어떤 이야기에 더 끌리나요?",
        options: [
            "A. “10년 넘게 꾸준히 이익 내는 회사 이야기”",
            "B. “미래 기술로 세상을 뒤집을 스타트업 이야기”", 
            "C. “요즘 사람들이 줄 서는 가게, 자주 쓰는 앱 이야기”",
        ],
        },
        {
        id: 3,
        question: "돈을 맡긴다면 나는 이렇게 하고 싶어요 !",
        options: [
            "A. 믿을 수 있고 탄탄한 곳에 오래 묵혀둔다.",
            "B. 새로운 아이디어와 성장 가능성 있는 곳에 과감히 건다.",
            "C. 내가 직접 써보고 괜찮은 곳에 소액씩 넓게 분산한다.",
        ],
        },
        {
        id: 4,
        question: "돈을 투자했는데 잠깐 떨어졌어요. 내 반응은?",
        options: [
            "A. “괜찮아, 오르든 내리든 나는 오래 들고 갈 거야.”",
            "B. “이건 오히려 기회야! 더 살까?”",
            "C. “이유가 뭘까? 뉴스나 주변 이야기를 찾아본다.”",
        ],
        },
        {
        id: 5,
        question: "투자 공부할 때 나는 이런 스타일 !",
        options: [
            "A. 숫자·기초부터 차근차근 배우는 게 좋다.",
            "B. 혁신 산업이나 기술 뉴스를 먼저 본다.",
            "C. 생활 속 변화나 주변 트렌드부터 관찰한다.", 
        ],
        },
    ];

    const handleSelect = (optionIndex) => {
        setAnswers((prev) => [...prev, optionIndex + 1]);

        if (step < 5) {
        setStep((prev) => prev + 1);
        } else {
        setLoading(true);
        setTimeout(() => {
            setLoading(false);
            const mentor = getMentor();
            setMentor(mentor);
            localStorage.setItem("assignedMentor", mentor);
            navigate("/result");
        }, 2000);
        }
    };

    const getMentor = () => {
        const counts = { 1: 0, 2: 0, 3: 0 };
        answers.forEach((num) => (counts[num] += 1));

        const max = Math.max(counts[1], counts[2], counts[3]);
        if (max === counts[1]) return "워렌 버핏";
        if (max === counts[2]) return "캐시 우드";
        return "피터 린치";
    };

    if (loading)
        return (
        <div className="loading-screen">
            <img src={cloud1} alt="loading background" className="bg-cloud" />
            <div className="loading-container">
            <div className="circle circle1"></div>
            <div className="circle circle2"></div>
            <div className="circle circle3"></div>
            </div>
            <p className="loading-text">멘토를 배정 중입니다!</p>
        </div>
        );

    const current = questions[step - 1];

    return (
        <div className="test-container">
        <img src={cloud1} alt="cloud background" className="bg-cloud" />

        <p className="test-step">
            <span translate="no">Q.</span> {step} / {questions.length}
        </p>


        <div className="question-box" translate="no">
            <h2 className="test-title" translate="no">{current.question}</h2>
        </div>

        <ul className="option-list">
            {current.options.map((opt, idx) => (
            <li key={idx}>
                <button
                className={`test-option option-${idx + 1}`}
                onClick={() => handleSelect(idx)}
                translate="no"
                >
                {opt}
                </button>
            </li>
            ))}
        </ul>
        </div>
    );
};

export default Test;
