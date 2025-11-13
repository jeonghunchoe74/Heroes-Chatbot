import React, { useRef, useState, useEffect, useLayoutEffect } from "react";
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

const API_BASE = "http://localhost:8000";

// 기존 mentorData(색상/배경/버튼/기본문구)는 그대로 유지
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
  const [mentor, setMentor] = useState(
    localStorage.getItem("assignedMentor") || "피터 린치"
  );

  // ✅ 백엔드 연동 추가 상태
  const [sessionId, setSessionId] = useState(null);
  const [introFromApi, setIntroFromApi] = useState("");       // intro 대체(백엔드)
  const [newsData, setNewsData] = useState([]);               // 카드뉴스(백엔드)
  const [loading, setLoading] = useState(false);

  const [selectedNews, setSelectedNews] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [messages, setMessages] = useState([]); // (필요 시 확장)
  const [inputText, setInputText] = useState("");
  const [visibleStep, setVisibleStep] = useState(0);
  const scrollRef = useRef(null);
  const savedScrollLeftRef = useRef(0);   // 클릭 시 scrollLeft 저장

  // mentor → guru_id 매핑
  const guruMap = { "워렌 버핏": "buffett", "피터 린치": "lynch", "캐시 우드": "wood" };
  const guru_id = guruMap[mentor] || "lynch";

  // 기존 타이밍 애니메이션 유지
  useEffect(() => {
    const timers = [ setTimeout(() => setVisibleStep(1), 1500),
                     setTimeout(() => setVisibleStep(2), 3000) ];
    return () => timers.forEach((t) => clearTimeout(t));
  }, []);

  // ✅ 초기 진입: 백엔드에서 intro + 뉴스 3건 로드
  useEffect(() => {
    const fetchInit = async () => {
      try {
        const res = await fetch(`${API_BASE}/chatbot/init/${guru_id}`);
        const data = await res.json();
        setSessionId(data.session_id || data.sessionId || null);
        // UI는 유지하되, intro 말풍선 내용만 백엔드 값으로 교체
        setIntroFromApi(data.intro || "");
        // 뉴스 카드는 하드코딩 대신 실시간 데이터
        setNewsData(Array.isArray(data.news) ? data.news : []);
      } catch (e) {
        console.error("초기 데이터 로드 실패:", e);
        setIntroFromApi(""); // 실패 시 기본 mentorData.intro 노출
        setNewsData([]);     // 카드 없을 수 있음
      }
    };
    fetchInit();
  }, [mentor]); // 멘토 바뀔 때마다 재로딩

  useLayoutEffect(() => {
  if (scrollRef.current) {
    const x = savedScrollLeftRef.current;
    // ✅ 브라우저의 자동 스크롤이 끝난 뒤 즉시 복원
    setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTo({ left: x, behavior: "auto" });
      }
    }, 0);
  }
}, [selectedNews, selectedNews?.comment]);

  // 기존 수평 카드 스크롤 로직 유지
  const viewportWidth = 260;
  const cardWidth = 220;
  const scrollToCard = (direction) => {
    const el = scrollRef.current;
    if (!el) return;
    const step = cardWidth + 33;
    const next =
      direction === "right"
        ? Math.min(el.scrollLeft + step, el.scrollWidth)
        : Math.max(el.scrollLeft - step, 0);
    el.scrollTo({ left: next, behavior: "smooth" });
  };

  const handleSelectNews = (news, index) => {
  if (scrollRef.current) {
    savedScrollLeftRef.current = scrollRef.current.scrollLeft; // ✅ 현재 위치 저장
  }
  setActiveIndex(index);      // 점(인디케이터) 동기화
  setSelectedNews(news);      // 상세패널 갱신
};


  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const idx = Math.round(el.scrollLeft / (cardWidth + 12));
      setActiveIndex(idx);
    };
    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [cardWidth]);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
    e.target.style.height = "auto";
    const newHeight = Math.min(e.target.scrollHeight, 54);
    e.target.style.height = `${newHeight}px`;
  };

  // ✅ 뉴스 "분석하기" → 백엔드 analyze 호출 → 말풍선 comment에 반영
  const analyzeNews = async (news, index) => {
    // ✅ 현재 가로 스크롤 위치 저장
    if (scrollRef.current) {
      savedScrollLeftRef.current = scrollRef.current.scrollLeft;
    }

    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/chatbot/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guru_id, content: news.summary || "" }),
      });
      const data = await res.json();
      const analysis = data.analysis || "분석 결과를 불러오지 못했습니다.";

      setActiveIndex(index); // ✅ 인디케이터(점) 동기화
      // 기존 UI 유지: 선택된 카드 하단 말풍선에 “comment”로 표시
      setSelectedNews((prev) => ({
        ...news,
        comment: analysis.replace(/<[^>]+>/g, ""), // 섹터 HTML 제거하고 말풍선에는 텍스트만
      }));
    } catch (e) {
      console.error("뉴스 분석 실패:", e);
    } finally {
      setLoading(false);
    }
  };

  // 기존 전송 버튼: 현재는 로컬 메시지
  // ✅ 챗봇 대화 복원
const handleSend = async () => {
  if (!inputText.trim()) return;

  const userMessage = { role: "user", content: inputText };
  setMessages((prev) => [...prev, userMessage]);
  setInputText("");
  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/chatbot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: inputText,
        guru_id,
        session_id: sessionId,
      }),
    });

    const data = await res.json();
    const botMessage = { role: "assistant", content: data.response || data.text };
    setMessages((prev) => [...prev, botMessage]);
    setSessionId(data.session_id);
  } catch (err) {
    console.error("GPT 대화 전송 실패:", err);
  } finally {
    setLoading(false);
  }
};


  const Row = ({ children, withAvatar = false }) => {
    const { avatar } = mentorData[mentor];
    return (
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
  };

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

  // mentorData에서 기본 테마/문구 가져오기
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
              justifyContent: "center",
              position: "relative",
            }}
          >
            <img
              src={menu}
              alt="menu"
              onClick={onOpenMenu}
              style={{ position: "absolute", left: 15, top: 14, width: 25, height: 25, cursor: "pointer" }}
            />
            <div style={{ color: "#27292E", fontSize: 16, fontWeight: 700 }}>{title}</div>
          </div>
        </div>

        {/* 채팅(기존 UI 유지, 단 데이터만 실시간) */}
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
            {/* ✅ intro: 백엔드 값이 있으면 교체, 없으면 기존 문구 */}
            <LeftBubble style={{ marginTop: 30 }}>
              {introFromApi || intro}
            </LeftBubble>
            {visibleStep >= 1 && <LeftBubble style={{ marginTop: 10 }}>{followUp}</LeftBubble>}

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
                {/* 카드 뉴스 */}
                <div style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
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

                  <div
                    ref={scrollRef}
                    style={{
                      width: viewportWidth,
                      height: 240,
                      overflowX: "auto",
                      display: "flex",
                      scrollSnapType: "x mandatory",
                      scrollbarWidth: "none",
                      overflowAnchor: "none",  // ✅ 브라우저 자동 스크롤 방지
                      scrollBehavior: "auto",   // ✅ 렌더 후 강제 애니메이션 방지
                    }}
                  >
                    <style>{`div::-webkit-scrollbar { display: none !important; }`}</style>

                    {/* ✅ 백엔드 뉴스 카드 */}
                    {newsData.map((news, i) => (
                      <div
                        key={i}
                        onClick={() => handleSelectNews(news, i)}
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
                          scrollSnapAlign: "start",                 // ✅ 스냅 정렬 고정
                        }}
                      >
                        <a
                          href={news.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: 12, fontWeight: 700, marginBottom: 11, textAlign: "center", color: "#1a0dab", textDecoration: "none" }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          {news.title}
                        </a>
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
                        <div style={{ fontSize: 10, color: "#444", lineHeight: "15px", textAlign: "left", width: "100%" }}>
                          {news.summary}
                        </div>
                        {/* 분석하기 버튼(기존 UI 배치 유지) */}
                        <button
                          onClick={(e) => { e.stopPropagation(); analyzeNews(news, i); }}
                          disabled={loading}
                          style={{
                            marginTop: 6,
                            alignSelf: "flex-start",
                            background: "#E9ECF2",
                            color: "#444",
                            border: "none",
                            borderRadius: 6,
                            padding: "3px 8px",
                            cursor: "pointer",
                            fontSize: 10,
                          }}
                        >
                          분석하기
                        </button>
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

                <div style={{ display: "flex", gap: 6, justifyContent: "center", marginTop: 4 }}>
                  {newsData.map((_, i) => (
                    <div
                      key={i}
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        backgroundColor: activeIndex === i ? "white" : "rgba(255,255,255,0.4)",
                        transition: "background 0.3s",
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* 카드 선택 시 기존 상세 패널 유지(설명 + 영향분석 틀 유지) */}
            {selectedNews && (
              <>
                <div
                  style={{
                    marginTop: 15,
                    width: 283,
                    background: mentorData[mentor].bubbleColor,
                    borderRadius: 10,
                    borderTopLeftRadius: 0,
                    padding: "10px 14px",
                    color: "#222",
                    fontSize: 11,
                    lineHeight: "18px",
                    textAlign: "left",
                  }}
                >
                  {/* 설명 */}
                  <div
                    style={{
                      background: "white",
                      borderRadius: 6,
                      padding: 8,
                      marginBottom: 10,
                      border: "1px solid #C5D8F1",
                    }}
                  >
                    <div style={{ fontWeight: 700, color: mentorData[mentor].themeColor, marginBottom: 8 }}>
                      📝 설명
                    </div>
                    <div style={{ fontSize: 10 }}>{selectedNews.summary}</div>
                  </div>

                  {/* 영향분석 (두 컬럼 틀은 유지, 내용은 분석 텍스트는 아래 말풍선에 표기) */}
                  <div
                    style={{
                      background: "white",
                      borderRadius: 6,
                      padding: 8,
                      border: "1px solid #C5D8F1",
                    }}
                  >
                    <div style={{ fontWeight: 700, color: mentorData[mentor].themeColor, marginBottom: 8 }}>
                      📊 영향분석
                    </div>
                    <div style={{ display: "flex", fontSize: 10 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: "#388E3C" }}>긍정요인</div>
                        {/* 백엔드가 리스트를 주지 않으므로 자리만 유지 */}
                        <div style={{ color: "#666", marginTop: 4 }}>• 분석 결과는 아래 말풍선에 표기됩니다.</div>
                      </div>
                      <div style={{ width: 1, backgroundColor: "#E0E0E0", margin: "0 8px" }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: "#D32F2F" }}>부정요인</div>
                        <div style={{ color: "#666", marginTop: 4 }}>• 분석 결과는 아래 말풍선에 표기됩니다.</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 분석 결과 말풍선(기존 UI 유지) */}
                {selectedNews.comment && (
                  <LeftBubble
                    style={{
                      marginTop: 12,
                      background: mentorData[mentor].bubbleColor,
                      maxWidth: 180,
                      whiteSpace: "pre-line",
                    }}
                  >
                    {selectedNews.comment.split("📊").map((part, idx) =>
                      idx === 0 ? (
                        <>{part.trim()}</>
                      ) : (
                        <div
                          key={idx}
                          style={{
                            marginTop: 10,
                            padding: "8px 10px",
                            borderRadius: 8,
                            background: "#F7F9FF",
                            fontSize: 10,
                            color: "#111",
                            lineHeight: "16px",
                          }}
                        >
                          📊 {part.trim()}
                        </div>
                      )
                    )}
                  </LeftBubble>
                )}
              </>
            )}
          </Row>
        </div>
        
        {/* GPT 대화 영역 (입력창 바로 위에 추가) */}
        <div
          style={{
            position: "absolute",
            bottom: 100, // 입력창 높이만큼 띄우기
            left: 0,
            width: "100%",
            maxHeight: 250, // 필요 시 높이 제한
            overflowY: "auto",
            padding: "0 12px 12px",
            boxSizing: "border-box",
            zIndex: 2, // 입력창 바로 위에 표시
          }}
        >
          {messages.map((msg, i) => (
            <div key={i} style={{ marginTop: 6 }}>
              <div
                style={{
                  background: msg.role === "user" ? "#444" : "white",
                  color: msg.role === "user" ? "white" : "#111",
                  borderRadius: 8,
                  padding: "6px 10px",
                  lineHeight: "18px",
                  fontSize: 13,
                }}
                dangerouslySetInnerHTML={{ __html: msg.content }}
              />
            </div>
          ))}
        </div>


        {/* 입력창 (기존 유지) */}
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
              src={mentorData[mentor].sendButton}
              alt="send"
              onClick={handleSend}
              style={{ width: 18, marginTop: 22, cursor: "pointer" }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatRoom;
