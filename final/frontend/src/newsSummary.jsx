import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import back from "./fonts/back.png";
import peterface from "./fonts/peterface.png";
import buffettface from "./fonts/buffettface.png";
import woodface from "./fonts/woodface.png";
import personchatback_peter from "./fonts/personchatback_peter.png";
import personchatback_buf from "./fonts/personchatback_buf.png";
import personchatback_wood from "./fonts/personchatback_wood.png";
import "./App.css";

const API_BASE = "http://localhost:8000";

const mentorData = {
    "피터 린치": {
        name: "피터 린치",
        img: peterface,
        background: personchatback_peter,
        guru_id: "lynch",
    },
    "워렌 버핏": {
        name: "워렌 버핏",
        img: buffettface,
        background: personchatback_buf,
        guru_id: "buffett",
    },
    "캐시 우드": {
        name: "캐시 우드",
        img: woodface,
        background: personchatback_wood,
        guru_id: "wood",
    },
};

const decodeHtmlEntities = (text) => {
    if (!text) return text;
    const textarea = document.createElement("textarea");
    textarea.innerHTML = text;
    return textarea.value;
};

function NewsSummary() {
    const navigate = useNavigate();
    const location = useLocation();
    
    // URL 파라미터나 localStorage에서 mentor 정보 가져오기
    const [mentor, setMentor] = useState(() => {
        const saved = localStorage.getItem("assignedMentor");
        return saved && mentorData[saved] ? saved : "피터 린치";
    });
    
    const [newsData, setNewsData] = useState([]);
    const [loading, setLoading] = useState(true);
    
    const current = mentorData[mentor];
    const guru_id = current.guru_id;

    useEffect(() => {
        const fetchNews = async () => {
            try {
                setLoading(true);
                const res = await fetch(`${API_BASE}/news/${guru_id}`);
                const data = await res.json();
                const newsList = Array.isArray(data.news) ? data.news.slice(0, 3) : [];
                setNewsData(newsList);
            } catch (err) {
                console.error("뉴스 로딩 실패:", err);
                setNewsData([]);
            } finally {
                setLoading(false);
            }
        };
        
        fetchNews();
    }, [guru_id]);

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
                    overflow: "auto",
                    backgroundImage: `url(${current.background})`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                }}
            >
                {/* 반투명 오버레이 */}
                <div
                    style={{
                        position: "absolute",
                        inset: 0,
                        backgroundColor: "rgba(255, 255, 255, 0.95)",
                        zIndex: 1,
                    }}
                />

                {/* 상단 헤더 */}
                <div style={{ position: "relative", zIndex: 2 }}>
                    <div
                        style={{
                            width: 402,
                            height: 60,
                            background: "#D9D9D9",
                        }}
                    />
                    <div
                        style={{
                            width: 402,
                            height: 55,
                            background: "white",
                            boxShadow: "0px 4px 120px rgba(57, 86, 77, 0.15)",
                            display: "flex",
                            alignItems: "center",
                            padding: "0 15px",
                        }}
                    >
                        <img
                            src={back}
                            alt="뒤로가기"
                            onClick={() => navigate(-1)}
                            style={{
                                width: 13,
                                height: 10,
                                cursor: "pointer",
                            }}
                        />
                        <div
                            style={{
                                flex: 1,
                                textAlign: "center",
                                color: "#27292E",
                                fontSize: 16,
                                fontWeight: 700,
                            }}
                        >
                            뉴스 정리본
                        </div>
                        <div style={{ width: 13 }} />
                    </div>
                </div>

                {/* 뉴스 리스트 */}
                <div
                    style={{
                        position: "relative",
                        zIndex: 2,
                        padding: "20px 20px 40px 20px",
                        marginTop: 115,
                    }}
                >
                    {loading ? (
                        <div
                            style={{
                                textAlign: "center",
                                padding: "40px 0",
                                color: "#666",
                                fontSize: 14,
                            }}
                        >
                            뉴스를 불러오는 중...
                        </div>
                    ) : newsData.length === 0 ? (
                        <div
                            style={{
                                textAlign: "center",
                                padding: "40px 0",
                                color: "#666",
                                fontSize: 14,
                            }}
                        >
                            뉴스가 없습니다.
                        </div>
                    ) : (
                        newsData.map((news, index) => (
                            <div
                                key={index}
                                style={{
                                    background: "white",
                                    borderRadius: 12,
                                    padding: 16,
                                    marginBottom: 20,
                                    boxShadow: "0px 2px 8px rgba(0, 0, 0, 0.1)",
                                }}
                            >
                                {/* 뉴스 번호 */}
                                <div
                                    style={{
                                        fontSize: 12,
                                        color: "#999",
                                        marginBottom: 8,
                                        fontWeight: 600,
                                    }}
                                >
                                    {index + 1}번째 뉴스
                                </div>

                                {/* 제목 */}
                                <div
                                    style={{
                                        fontSize: 16,
                                        fontWeight: 700,
                                        color: "#27292E",
                                        marginBottom: 12,
                                        lineHeight: "22px",
                                    }}
                                >
                                    {news.link ? (
                                        <a
                                            href={news.link}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                color: "#27292E",
                                                textDecoration: "none",
                                            }}
                                            onMouseEnter={(e) => {
                                                e.target.style.color = "#5BA1E9";
                                                e.target.style.textDecoration = "underline";
                                            }}
                                            onMouseLeave={(e) => {
                                                e.target.style.color = "#27292E";
                                                e.target.style.textDecoration = "none";
                                            }}
                                        >
                                            {decodeHtmlEntities(news.title)}
                                        </a>
                                    ) : (
                                        decodeHtmlEntities(news.title)
                                    )}
                                </div>

                                {/* 이미지 영역 (뉴스 이미지가 있으면 표시, 없으면 기본 아이콘) */}
                                <div
                                    style={{
                                        width: "100%",
                                        height: 180,
                                        borderRadius: 8,
                                        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        marginBottom: 12,
                                        overflow: "hidden",
                                    }}
                                >
                                    {news.image ? (
                                        <img
                                            src={news.image}
                                            alt={news.title}
                                            style={{
                                                width: "100%",
                                                height: "100%",
                                                objectFit: "cover",
                                            }}
                                        />
                                    ) : (
                                        <span style={{ fontSize: 48 }}>📰</span>
                                    )}
                                </div>

                                {/* 요약 */}
                                <div
                                    style={{
                                        fontSize: 13,
                                        color: "#555",
                                        lineHeight: "20px",
                                        marginBottom: 8,
                                    }}
                                >
                                    {decodeHtmlEntities(news.summary || news.description || "")}
                                </div>

                                {/* 출처 및 날짜 */}
                                {(news.source || news.pubDate) && (
                                    <div
                                        style={{
                                            fontSize: 11,
                                            color: "#999",
                                            marginTop: 8,
                                            paddingTop: 8,
                                            borderTop: "1px solid #eee",
                                        }}
                                    >
                                        {news.source && news.source !== "offline" && (
                                            <span>출처: {news.source}</span>
                                        )}
                                        {news.pubDate && (
                                            <span style={{ marginLeft: news.source ? 8 : 0 }}>
                                                {news.pubDate}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

export default NewsSummary;

