import React, {useState} from "react";
import { useNavigate } from "react-router-dom";
import { useMentor } from "./mentorContext"; 
import "./App.css";
import Cloud2 from "./fonts/Cloud2.png"; 
import back from "./fonts/back.png"; 
import peter from "./fonts/peter.png";
import cathie from "./fonts/cathie.png";
import buffett from "./fonts/buffett.png";

const mentorData = {
    "피터 린치": {
        img: peter,
        engName : "Peter Lynch",
        color: "#2580DE",
        subColor: "#91b8dfff",
        subColor2: "#e1eaf3ff",
        cardBg: "#ffffffff",
        cardBorder: "#000000",
        tags: ["삼성전자", "LG화학"],
    },
    "워렌 버핏": { 
        img: buffett,
        engName : "Warren Buffett",
        color: "#8DC70D",
        subColor: "#c2d499ff",
        subColor2: "#e4eecfff",
        cardBg: "#ffffffff",
        cardBorder: "#000000",
        tags: ["애플", "코카콜라"],
    },
    "캐시 우드": {
        img: cathie,
        engName : "Cathie Wood",
        color: "#EF5A56",
        subColor: "#ecb3b1ff",
        subColor2: "#f8e2e1ff",
        cardBg: "#ffffffff",
        cardBorder: "#000000",
        tags: ["테슬라", "엔비디아"],
    },
};

function RoomChoose({ onBack }) {
    const { getMentor, saveMentor } = useMentor(); 
    const mentorName = getMentor("chooseRoomMentor") || "피터 린치";
    const mentor = mentorData[mentorName];
    const navigate = useNavigate(); 

    // ✅ 선택된 태그 상태 추가
    const [selectedTag, setSelectedTag] = useState(null);

    // ✅ 검색어 상태
    const [searchTerm, setSearchTerm] = useState("");
    const [filteredTags, setFilteredTags] = useState([]);

    // ✅ 선택 시 input에 값 고정 + 비활성화
    const persistRoom = (value) => {
        const v = (value || "").trim();
        if (!v) return;
        try { localStorage.setItem("room", v); } catch {}
    };

    const handleTagClick = (tag) => {
        setSelectedTag(tag);
        setSearchTerm(tag); // input에 선택한 종목 이름 표시
        saveMentor("chooseRoomStock", tag);
        persistRoom(tag);
        setFilteredTags([]);
    };

    // ✅ input 수정 시 자동완성 업데이트
    const handleSearchChange = (e) => {
        const value = e.target.value;
        setSearchTerm(value);
        setSelectedTag(null); // 다시 검색 시작하면 선택 해제

        if (value.trim() === "") {
            setFilteredTags([]);
        } else {
            const matches = mentor.tags.filter((tag) =>
                tag.toLowerCase().includes(value.toLowerCase())
            );
            setFilteredTags(matches);
        }
    };
    

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
                    <div style={{ fontSize: 14, fontWeight: "700", lineHeight: "25px" }}>({mentor.engName})</div>
                </div>

                {/* 검색창 */}
                <div style={{ left: 20, top: 500, position: "absolute", textAlign: "center", color: "black", fontSize: 15, fontFamily: "SF Pro", fontWeight: "590", lineHeight: "25px" }}>
                    종목을 검색해주세요
                </div>

                {/* ✅ input 직접 사용 */}
                <input
                    type="text"
                    value={searchTerm}
                    onChange={handleSearchChange}
                    onBlur={() => persistRoom(searchTerm)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            e.preventDefault();
                            persistRoom(searchTerm);
                        }
                    }}
                    placeholder={selectedTag ? "" : "예: 키움증권"}
                    style={{
                        width: 362,
                        height: 38,
                        left: 20,
                        top: 530,
                        position: "absolute",
                        borderRadius: 10,
                        border: "1px solid #ccc",
                        paddingLeft: 10,
                        fontSize: 12,
                        fontFamily: "SF Pro",
                    }}
                />

                {/* ✅ 자동완성 리스트 */}
                {filteredTags.length > 0 && (
                    <div
                        style={{
                            position: "absolute",
                            top: 570,
                            left: 20,
                            width: 362,
                            background: "white",
                            border: "1px solid #ccc",
                            borderRadius: 10,
                            zIndex: 10,
                            boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
                        }}
                    >
                        {filteredTags.map((tag, index) => (
                            <div
                                key={index}
                                onClick={() => handleTagClick(tag)}
                                style={{
                                    padding: "8px 12px",
                                    cursor: "pointer",
                                    fontSize: 13,
                                    color: "#333",
                                    borderBottom:
                                        index < filteredTags.length - 1
                                            ? "1px solid #eee"
                                            : "none",
                                    background:
                                        selectedTag === tag ? "#E2F2FF" : "white",
                                }}
                            >
                                {tag}
                            </div>
                        ))}
                    </div>
                )}

                {/* 추천 종목 태그 */}
                    {mentor.tags.map((tag, idx) => {
                    const isSelected = selectedTag === tag;
                    return (
                        <React.Fragment key={idx}>
                            <div
                                key={idx}
                                onClick={() => handleTagClick(tag)}
                                style={{
                                    width: 62,
                                    height: 26,
                                    left: 20 + idx * 76,
                                    top: 590,
                                    position: "absolute",
                                    background: mentor.subColor2,
                                    borderRadius: 15,
                                    cursor: "pointer",
                                    border: isSelected ? "2px solid #626262ff" : "none",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    color:  "#5E5E5E",
                                    fontSize: 10,
                                    fontFamily: "SF Pro",
                                    fontWeight: "510",
                                    transition: "all 0.2s ease",
                                    userSelect: "none",
                                }}
                            >
                                {tag}
                            </div>
                        </React.Fragment>
                    );
                })}
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
                    onClick={() => {
                        // 선택한 종목을 room에 저장 (태그 선택 없으면 입력값 사용)
                        const currentRoom = (selectedTag || searchTerm || "").trim();
                        if (currentRoom) {
                            try { localStorage.setItem("room", currentRoom); } catch {}
                        }
                        // 닉네임 입력받기
                        const name = (window.prompt("닉네임을 입력하세요") || "").trim();
                        if (!name) return;
                        try { localStorage.setItem("displayName", name); } catch {}
                        // 바로 채팅 화면으로 이동 (manyChat에서 자동 조인)
                        navigate("/group-chat");
                    }}
                >
                    <div
                        style={{
                            width: 83,
                            left: 138,
                            top: 13,
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
                        background: mentor.subColor,
                        border: "2px solid black",
                        cursor: "pointer",
                    }}
                    onClick={() => navigate("/create")}
                >
                    <div
                        style={{
                            width: 105,
                            left: 34,
                            top: 12,
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
                        background: mentor.subColor,
                        border: "2px solid black",
                        cursor: "pointer",
                    }}
                    onClick={() => navigate("/invited")}
                >
                    <div
                        style={{
                            width: 104,
                            left: 34,
                            top: 12,
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
