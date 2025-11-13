import React from "react";
import { useNavigate } from "react-router-dom";
import back from "./fonts/back.png";
import noise from "./fonts/noise.png";
import woodface from "./fonts/woodface.png";
import buffettface from "./fonts/buffettface.png";
import peterface from "./fonts/peterface.png";

function MyPage() {
    const navigate = useNavigate();
    const mentorImages = {
        "워렌 버핏": buffettface,
        "캐시 우드": woodface,
        "피터 린치": peterface,
    };

    return (
        <div
        style={{
            width: "100vw",
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-start",
        }}
        >
        {/* ✅ 실제 컨테이너 */}
        <div
            style={{
            width: 402,
            height: 874,
            position: "relative",
            backgroundColor: "#EEEEEE",
            overflow: "hidden",
            }}
        >
            {/* ✅ 노이즈 오버레이 */}
            <div
            style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                backgroundImage: `url(${noise})`,
                backgroundRepeat: "repeat",
                backgroundSize: "auto",
                opacity: 0.3,
                mixBlendMode: "multiply",
                pointerEvents: "none",
                zIndex: 1,
            }}
            />

            {/* ✅ 여기에 모든 콘텐츠를 감쌈 (글자가 위로 올라오게) */}
            <div
            style={{
                position: "relative",
                zIndex: 2,
            }}
            >
            {/* 상단 헤더 */}
            <div
                style={{
                width: 402,
                height: 49,
                top: 62,
                left: 0,
                position: "absolute",
                background: "white",
                borderTop: "1px solid #BEBEBE",
                borderBottom: "1px solid #BEBEBE",
                }}
            ></div>

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

            {/* 타이틀 */}
            <div
                style={{
                top: 75,
                left: 159,
                position: "absolute",
                color: "black",
                fontSize: 16,
                fontFamily: "SF Pro",
                fontWeight: 700,
                }}
            >
                마이페이지
            </div>

            {/* 큰 테두리 박스 */}
            <div
                style={{
                width: 362,
                height: 380,
                top: 150,
                left: 20,
                position: "absolute",
                background: "rgba(217,217,217,0.3)",
                border: "1px solid black",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                paddingTop: "10px",
                }}
            >
                {/* 제목 */}
                <div
                style={{
                    textAlign: "center",
                    color: "black",
                    fontSize: 15,
                    fontFamily: "SF Pro",
                    fontWeight: 700,
                    marginBottom: "10px",
                }}
                >
                나의 스터디
                </div>

                {/* 구분선 */}
                <div
                style={{
                    width: "85%",
                    height: "1px",
                    backgroundColor: "#BEBEBE",
                    opacity: 0.8,
                    marginBottom: "20px",
                }}
                ></div>

                {/* 카드들 */}
                {[
                { name: "삼성전자", mentor: "워렌 버핏" },
                { name: "엔비디아", mentor: "캐시 우드" },
                { name: "테슬라", mentor: "피터 린치" },
                { name: "팔란티어", mentor: "워렌 버핏" },
                ].map((item, idx) => (
                <div
                    key={idx}
                    style={{
                    width: 306,
                    height: 65,
                    background: "white",
                    border: "0.5px solid black",
                    marginBottom: "10px",
                    display: "flex",
                    flexDirection: "row",
                    alignItems: "center",
                    gap: "10px",
                    paddingLeft: "10px",
                    }}
                >
                    <img
                    src={mentorImages[item.mentor]}
                    alt={item.mentor}
                    style={{
                        width: 40,
                        borderRadius: "50%",
                        objectFit: "cover",
                        display: "block",
                        marginTop: "21px",
                    }}
                    />

                    <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "flex-start",
                        justifyContent: "center",
                    }}
                    >
                    <div
                        style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color: "black",
                        fontFamily: "SF Pro",
                        }}
                    >
                        {item.name}{" "}
                        <span style={{ fontSize: 9 }}>({item.mentor})</span>
                    </div>
                    <div
                        style={{
                        fontSize: 9,
                        fontWeight: 400,
                        color: "black",
                        marginTop: "3px",
                        textAlign: "left",
                        }}
                    >
                        미래 성장성이 정말 시장이 기대하는 만큼 지속 가능할까?
                    </div>
                    </div>
                </div>
                ))}
            </div>

            {/* 박스 아래 연한 구분선 */}
            <div
                style={{
                width: 362,
                height: "1px",
                left: 20,
                top: 570,
                position: "absolute",
                backgroundColor: "#BEBEBE",
                opacity: 0.6,
                }}
            ></div>

            {/* 영웅의 멘토링 / 영웅과 스터디 버튼 간단형 */}
            <div
                style={{
                width: 362,
                left: 20,
                top: 590,
                position: "absolute",
                display: "flex",
                flexDirection: "column",
                gap: "15px",
                alignItems: "center",
                }}
            >
                <div
                onClick={() => navigate("/chat")}
                style={{
                    width: 362,
                    height: 45,
                    background: "rgba(247, 199, 96, 0.15)",
                    border: "1px solid #C13A00",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 16,
                    fontFamily: "Hakgyoansim_PosterOTFB",
                    color: "#2E2E2E",
                    cursor: "pointer",
                }}
                >
                🌱 영웅의 멘토링
                </div>

                <div
                onClick={() => navigate("/chat")}
                style={{
                    width: 362,
                    height: 45,
                    background: "rgba(117, 216, 120, 0.16)",
                    border: "1px solid #085D05",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 16,
                    fontFamily: "Hakgyoansim_PosterOTFB",
                    color: "#2E2E2E",
                    cursor: "pointer",
                }}
                >
                📖 영웅과 스터디
                </div>
            </div>

            {/* 박스 아래 연한 구분선 */}
            <div
                style={{
                width: 362,
                height: "1px",
                left: 20,
                top: 720,
                position: "absolute",
                backgroundColor: "#BEBEBE",
                opacity: 0.5,
                }}
            ></div>

            {/* 하단 명언 */}
            <div
                style={{
                width: 362,
                height: 56,
                left: 20,
                top: 753,
                position: "absolute",
                opacity: 0.7,
                background: "rgba(182,182,182,0.46)",
                border: "1px solid black",
                }}
            />
            <div
                style={{
                left: 112,
                top: 760,
                position: "absolute",
                textAlign: "center",
                color: "#3D3A3A",
                fontSize: 12,
                fontFamily: "SF Pro",
                fontWeight: 700,
                lineHeight: "25px",
                }}
            >
                “주식 투자는 과학이 아니라 예술이다”
            </div>
            <div
                style={{
                left: 164,
                top: 779,
                position: "absolute",
                textAlign: "center",
                color: "#3D3A3A",
                fontSize: 9,
                fontFamily: "SF Pro",
                fontWeight: 700,
                lineHeight: "25px",
                }}
            >
                - Peter Lynch -
            </div>
            </div>
        </div>
        </div>
    );
}

export default MyPage;
