import { BrowserRouter, Routes, Route } from "react-router-dom";
import { MentorProvider } from "./mentorContext";
import React, { useState } from "react";
import './App.css';
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


function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  return (
  <MentorProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Home />} />
        <Route path="/mypage" element={<MyPage />} />
        <Route path="/test" element={<Test />} />
        <Route path="/result" element={<Result />} />
        <Route path="/choose-men" element={<ChooseMen />} />
        <Route path="/choose-room" element={<RoomChoose />} />
        <Route path="/group-chat" element={<ManyChat />} />
        <Route
          path="/chat"
          element={
            <div style={{ position: "relative", width: "100%", height: "100%" }}>
              {/* ChatRoom 본체 */}
              <ChatRoom onOpenMenu={() => setIsMenuOpen(true)} />

              {/* Menu 오버레이 */}
              {isMenuOpen && (
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    zIndex: 999,
                    transition: "transform 0.3s ease",
                    transform: isMenuOpen
                      ? "translateX(0)"
                      : "translateX(100%)",
                  }}
                >
                  <Menu
                    onBack={() => setIsMenuOpen(false)}
                    onChangeHero={() => {
                      alert("영웅 바꾸기 화면으로 이동!");
                      setIsMenuOpen(false);
                    }}
                  />
                </div>
              )}
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
    </MentorProvider>
  );
}

export default App;
