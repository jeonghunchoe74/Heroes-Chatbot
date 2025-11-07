
import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.css';

const API_BASE_URL = 'http://localhost:8000';

export default function Chatbot({ onBack }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  const focusInput = () => {
    if (inputRef.current) inputRef.current.focus();
  };

  // 스크롤을 항상 최신 메시지로 이동
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    const messageContent = input;
    setInput('');
    setLoading(true);

    // 🖐️ 메시지를 보낼 때 버핏이 손 흔듦 🗣️ 메시지를 보낼 때 버핏이 말하는 듯한 애니메이션
    const mascot = document.querySelector('.mascot');
    if (mascot) {
      mascot.classList.add('talk', 'wave');
      setTimeout(() => mascot.classList.remove('talk', 'wave'), 1200);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chatbot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageContent,
          session_id: sessionId
        })
      });
      if (!response.ok) {
        throw new Error(`서버 오류: ${response.status}`);
      }

      const data = await response.json();

      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
        console.log('새 세션 ID 저장:', data.session_id);
      }

      const botMessage = { role: 'assistant', content: data.response };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('전송 실패:', error);
      const errorMessage = {
        role: 'assistant',
        content: '오류가 발생했습니다. 서버를 확인해주세요.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      focusInput();
    }
  };

  const handleReset = async () => {
    setMessages([]);
    setSessionId(null);

    try {
      const response = await fetch(`${API_BASE_URL}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });

      if (response.ok) {
        console.log('대화가 초기화되었습니다.');
      }
    } catch (error) {
      console.error('리셋 실패:', error);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="stage">
      <div className="phone">
        {/* 상단 바 */}
        <div className="topbar">
          {onBack && (
            <button className="back-icon" onClick={onBack} aria-label="뒤로가기">
              ←
            </button>
          )}
          <div className="title">
            <div className="avatar">
              {/* 이미지가 없을 경우를 대비해 이모지 폴백 */}
              <img
                src="/assets/warren-avatar.png"    
                alt="워렌 버핏"
                onError={(e) => (e.currentTarget.style.display = 'none')}
              />
            </div>
            <div className="name">워렌 버핏</div>
          </div>
          <div className="actions">
            <button className="reset-icon" onClick={handleReset} title="대화 초기화">⟲</button>
          </div>
        </div>

        {/* 채팅 영역 (칠판 배경) */}
        <div className="chalkboard" ref={scrollRef}>
          {messages.length === 0 && !loading && (
            <div className="empty-hint">“입력…”에 질문을 적어보세요.</div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              <div className={`message ${msg.role}`}>{msg.content}</div>
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

          {/* 마스코트 (하단 고정) */}
          <div className="mascot" aria-hidden>
            <img
              src="/assets/warren-mascot.png"
              alt="워렌 버핏 마스코트"
              onError={(e) => (e.currentTarget.style.display = 'none')}
            />
          </div>
        </div>

        {/* 하단 입력 바 */}
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
              title="보내기"
            >
              <span className="arrow" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
