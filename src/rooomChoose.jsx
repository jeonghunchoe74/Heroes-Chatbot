import React from "react";
import { useNavigate } from "react-router-dom";
import { useMentor } from "./mentorContext"; 
import "./App.css";
import Cloud2 from "./fonts/Cloud1.png"; 
import back from "./fonts/back.png"; 
import peter from "./fonts/peter.png";
import cathie from "./fonts/cathie.png";
import buffett from "./fonts/buffett.png";

const mentorData = {
    "피터 린치": {
        img: peter,
        color: "#2580DE",
        cardBg: "#F5F5F5",
        cardBorder: "#000000",
        tags: ["삼성전자", "LG화학"],
    },
    "워렌 버핏": {
        img: buffett,
        color: "#9FDD18",
        cardBg: "#F5F5F5",
        cardBorder: "#000000",
        tags: ["애플", "코카콜라"],
    },
    "캐시 우드": {
        img: cathie,
        color: "#EF5A56",
        cardBg: "#F5F5F5",
        cardBorder: "#000000",
        tags: ["테슬라", "엔비디아"],
    },
};

function RoomChoose({ onBack }) {
    const { getMentor } = useMentor(); 
    const mentorName = getMentor("chooseRoomMentor") || "피터 린치";
    const mentor = mentorData[mentorName];
    const navigate = useNavigate(); 

    return (
        <div style={{ width: "100vw", display: "flex", justifyContent: "center", alignItems: "center" }}>
            <div
                style={{
                    width: 402,
                    height: 874,
                    position: "relative",
                    backgroundImage: `url(${Cloud2})`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                    overflow: "hidden",
                }}
            >
                <div style={{ position: "absolute", inset: 0, backgroundColor: "rgba(255,255,255,0.7)" }} />

                {/* 상단 헤더 */}
                <div
                    style={{
                        width: "100%",
                        height: 49,
                        top: 62,
                        left: 0,
                        position: "absolute",
                        background: "white",
                        boxShadow: "0px 4px 80px rgba(0,0,0,0.1)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderBottom: "1px solid #BEBEBE",
                        borderTop: "1px solid #BEBEBE",
                    }}
                >
                    <img
                        src={back}
                        alt="back"
                        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate("/home"))}
                        style={{
                            position: "absolute",
                            top: 20,
                            left: 25,
                            height: 8,
                            width: "auto",
                            cursor: "pointer",
                            zIndex: 1000,
                        }}
                    />
                    <div style={{ textAlign: "center", color: "black", fontSize: 16, fontFamily: "SF Pro", fontWeight: "700" }}>
                        영웅과 함께
                    </div>
                </div>

                {/* 멘토 카드 */}
                <div
                    style={{
                        width: 362,
                        height: 312,
                        left: 20,
                        top: 142,
                        position: "absolute",
                        background: mentor.cardBg,
                        border: `2px solid ${mentor.cardBorder}`,
                    }}
                />
                <img
                    style={{ width: 147, height: 220, left: 125, top: 159, position: "absolute" }}
                    src={mentor.img}
                    alt={mentorName}
                />
                <div style={{ width: 180, left: 109, top: 383, position: "absolute", textAlign: "center", color: "black", fontFamily: "SF Pro" }}>
                    <div style={{ fontSize: 20, fontWeight: "700", lineHeight: "25px" }}>{mentorName}</div>
                    <div style={{ fontSize: 14, fontWeight: "700", lineHeight: "25px" }}>({mentorName})</div>
                </div>

                {/* 검색창 */}
                <div style={{ left: 20, top: 500, position: "absolute", textAlign: "center", color: "black", fontSize: 15, fontFamily: "SF Pro", fontWeight: "590", lineHeight: "25px" }}>
                    종목을 검색해주세요
                </div>
                <div style={{ width: 362, height: 38, left: 20, top: 530, position: "absolute", background: "white", borderRadius: 10, border: "1px solid #ccc" }} />
                <div style={{ left: 30, top: 537, position: "absolute", color: "#9D9D9D", fontSize: 11, fontFamily: "SF Pro", fontWeight: "590" }}>
                    예: 키움증권
                </div>

                {/* 추천 종목 태그 */}
                {mentor.tags.map((tag, idx) => (
                    <React.Fragment key={idx}>
                        <div
                            style={{
                                width: 62,
                                height: 26,
                                left: 20 + idx * 76,
                                top: 577,
                                position: "absolute",
                                background: "#E2F2FF",
                                borderRadius: 15,
                                cursor: "pointer",
                            }}
                            onClick={() => saveMentor("chooseRoomStock", tag)} // ✅ 클릭 시 저장
                        />
                        <div
                            style={{
                                left: 32 + idx * 76,
                                top: 583,
                                position: "absolute",
                                color: "#5E5E5E",
                                fontSize: 10,
                                fontFamily: "SF Pro",
                                fontWeight: "510",
                            }}
                        >
                            {tag}
                        </div>
                    </React.Fragment>
                ))}

                {/* 구분선 */}
                <div style={{ width: 362, height: 0, left: 20, top: 634, position: "absolute", borderTop: "1.2px solid #B2ADAD" }} />

                {/* 방 참가하기 */}
                <div
                    style={{
                        width: 362,
                        height: 52,
                        left: 20,
                        top: 663,
                        position: "absolute",
                        background: mentor.color, // 멘토 색상
                        border: "2px solid black",
                        cursor: "pointer",
                    }}
                    onClick={() => navigate("/group-chat")}
                >
                    <div
                        style={{
                            width: 83,
                            left: 160,
                            top: 10,
                            position: "absolute",
                            textAlign: "center",
                            color: "white",
                            fontSize: 17,
                            fontFamily: "SF Pro",
                            fontWeight: "700",
                        }}
                    >
                        방 참가하기
                    </div>
                </div>

                {/* 방 생성하기 */}
                <div
                    style={{
                        width: 172,
                        height: 52,
                        left: 19,
                        top: 727,
                        position: "absolute",
                        background: "#84BBF3",
                        border: "2px solid black",
                        cursor: "pointer",
                    }}
                    onClick={() => navigate("/create")}
                >
                    <div
                        style={{
                            width: 105,
                            left: 52,
                            top: 10,
                            position: "absolute",
                            textAlign: "center",
                            color: "white",
                            fontSize: 17,
                            fontFamily: "SF Pro",
                            fontWeight: "700",
                        }}
                    >
                        방 생성하기
                    </div>
                </div>

                {/* 초대받은 방 */}
                <div
                    style={{
                        width: 171,
                        height: 52,
                        left: 211,
                        top: 727,
                        position: "absolute",
                        background: "#84BBF3",
                        border: "2px solid black",
                        cursor: "pointer",
                    }}
                    onClick={() => navigate("/invited")}
                >
                    <div
                        style={{
                            width: 104,
                            left: 244,
                            top: 10,
                            position: "absolute",
                            textAlign: "center",
                            color: "white",
                            fontSize: 17,
                            fontFamily: "SF Pro",
                            fontWeight: "700",
                        }}
                    >
                        초대받은 방
                    </div>
                </div>
            </div>
        </div>
    );
}

export default RoomChoose;
