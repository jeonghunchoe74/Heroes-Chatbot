import React, { useState, useRef, useEffect } from "react";
import "./Chatbot.css";

const API_BASE_URL = "http://localhost:8000";

export default function Chatbot({ onBack }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [selectedGuru, setSelectedGuru] = useState("buffett"); // ✅ 대가 선택 기본값
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  // 입력창 포커스
  const focusInput = () => {
    if (inputRef.current) inputRef.current.focus();
  };

  // 🧩 스크롤 항상 최신으로 이동
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // 🧠 컴포넌트 첫 진입 시 — 대가 철학 + 최신 뉴스 자동 표시
  useEffect(() => {
    const fetchInit = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/chatbot/init/${selectedGuru}`);
        if (!res.ok) throw new Error(`서버 오류: ${res.status}`);
        const data = await res.json();

        // 철학과 뉴스 카드 메시지로 출력
        setMessages([
          { role: "assistant", type: "text", content: data.intro },
          { role: "assistant", type: "news", news: data.news }, 
        ]);
      } catch (err) {
        console.error("초기 데이터 로드 실패:", err);
        setMessages([
          { role: "assistant", content: "초기 데이터를 불러오지 못했습니다." },
        ]);
      }
    };
    fetchInit();
  }, [selectedGuru]);

  // 📨 메시지 전송
  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const messageContent = input;
    setInput("");
    setLoading(true);

    // 🎭 마스코트 애니메이션
    const mascot = document.querySelector(".mascot");
    if (mascot) {
      mascot.classList.add("talk", "wave");
      setTimeout(() => mascot.classList.remove("talk", "wave"), 1200);
    }

    try {
      const res = await fetch(`${API_BASE_URL}/chatbot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageContent,
          session_id: sessionId,
          guru_id: selectedGuru,
        }),
      });
      if (!res.ok) throw new Error(`서버 오류: ${res.status}`);
      const data = await res.json();

      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }
      const botMessage = { role: "assistant", content: data.response };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("전송 실패:", error);
      const errorMessage = {
        role: "assistant",
        content: "⚠️ 오류가 발생했습니다. 서버를 확인해주세요.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      focusInput();
    }
  };

  // 엔터키 전송
  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  // 초기화 버튼
  const handleReset = async () => {
    setMessages([]);
    setSessionId(null);
    try {
      await fetch(`${API_BASE_URL}/chatbot/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch (error) {
      console.error("리셋 실패:", error);
    }
  };

  // 📰 뉴스 카드 렌더링
  const renderNewsCards = (news) => (
    <div>
      <p>📰 최근 관심 뉴스예요 👇</p>
      {news.map((n, i) => (
        <div key={i} className="news-card">
          <a href={n.url} target="_blank" rel="noopener noreferrer">
            <strong>{n.title}</strong>
          </a>
          <p>{n.summary}</p>
          <button
            className="analyze-btn"
            onClick={() => analyzeArticle(n)}
            disabled={loading}
          >
            🔍 분석하기
          </button>
        </div>
      ))}
    </div>
  );

  // 🔎 뉴스 분석 버튼 동작
  const analyzeArticle = async (n) => {
    try {
      const res = await fetch(`${API_BASE_URL}/chatbot/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guru_id: selectedGuru,
          content: n.summary,
        }),
      });
      if (!res.ok) throw new Error(`서버 오류: ${res.status}`);
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.analysis },
      ]);
    } catch (err) {
      console.error("분석 실패:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "뉴스 분석 중 오류가 발생했습니다." },
      ]);
    }
  };

  return (
    <div className="stage">
      <div className="phone">
        {/* 상단 바 */}
        <div className="topbar">
          {onBack && (
            <button className="back-icon" onClick={onBack}>
              ←
            </button>
          )}
          <div className="title">
            <div className="avatar">
              <img
                src="/assets/warren-avatar.png"
                alt="워렌 버핏"
                onError={(e) => (e.currentTarget.style.display = "none")}
              />
            </div>
            {/* 대가 선택 */}
            <select
              className="guru-dropdown"
              value={selectedGuru}
              onChange={(e) => setSelectedGuru(e.target.value)}
            >
              <option value="buffet">워렌 버핏</option>
              <option value="lynch">피터 린치</option>
              <option value="wood">캐시 우드</option>
            </select>
          </div>
          <div className="actions">
            <button className="reset-icon" onClick={handleReset}>
              ⟲
            </button>
          </div>
        </div>

        {/* 채팅 영역 */}
        <div className="chalkboard" ref={scrollRef}>
          {messages.length === 0 && !loading && (
            <div className="empty-hint">“입력…”에 질문을 적어보세요.</div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              {msg.type === "news" ? (
                // 뉴스 카드는 JSX로 직접 렌더
                <div className={`message ${msg.role}`}>
                  {renderNewsCards(msg.news)}
                </div>
              ) : (
                // 텍스트/HTML만 dangerouslySetInnerHTML로 렌더 (자식 넣으면 에러)
                <div
                  className={`message ${msg.role}`}
                  dangerouslySetInnerHTML={{
                    __html:
                      typeof msg.content === "string"
                        ? msg.content
                        : String(msg.content),
                  }}
                />
              )}
            </div>
          ))}

          {loading && (
            <div className="message-wrapper assistant">
              <div className="message loading">
                <div className="loading-dots">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            </div>
          )}

          {/* 마스코트 */}
          <div className="mascot" aria-hidden>
            <img
              src="/assets/warren-mascot.png"
              alt="워렌 버핏 마스코트"
              onError={(e) => (e.currentTarget.style.display = "none")}
            />
          </div>
        </div>

        {/* 하단 입력창 */}
        <div className="input-bar">
          <div className="input-pill">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="입력..."
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={loading || !input.trim()}
              aria-label="보내기"
            >
              <span className="arrow" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
