import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { MentorProvider } from "./mentorContext";
import React, { useState, useEffect } from "react";
import "./App.css";
import Landing from "./landing";
import Home from "./home";
import Test from "./test";
import Result from "./result";
import ChatRoom from "./chatRoom";
import MyPage from "./mypage";
import Menu from "./menu";
import ChooseMen from "./chooseMen";
import RoomChoose from "./rooomChoose";
import ManyChat from "./manyChat";
import ChoosePer from "./chooseper";

function AppContent() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  // ✅ 경로 바뀌면 자동으로 메뉴 닫기
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/home" element={<Home />} />
      <Route path="/mypage" element={<MyPage />} />
      <Route path="/test" element={<Test />} />
      <Route path="/result" element={<Result />} />
      <Route path="/choose-men" element={<ChooseMen />} />
      <Route path="/choose-room" element={<RoomChoose />} />
      <Route path="/group-chat" element={<ManyChat />} />
      <Route path="/chooseper" element={<ChoosePer />} />
      <Route
        path="/chat"
        element={
          <div style={{ position: "relative", width: "100%", height: "100%" }}>
            <ChatRoom onOpenMenu={() => setIsMenuOpen(true)} />

            {isMenuOpen && (
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  zIndex: 999,
                }}
              >
                <Menu onBack={() => setIsMenuOpen(false)} />
              </div>
            )}
          </div>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <MentorProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </MentorProvider>
  );
}

export default App;