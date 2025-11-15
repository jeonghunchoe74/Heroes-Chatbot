import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import noise from "./fonts/noise.png";
import logo from "./fonts/logo.png";

function Home() {
  const navigate = useNavigate();
  const [fade, setFade] = useState(0);

  useEffect(() => {
    const fadeInTimer = setTimeout(() => setFade(1), 1100);
    const fadeOutTimer = setTimeout(() => setFade(0), 21000);
    const navigateTimer = setTimeout(() => navigate("/home"), 2600);

    return () => {
      clearTimeout(fadeInTimer);
      clearTimeout(fadeOutTimer);
      clearTimeout(navigateTimer);
    };
  }, [navigate]);

  return (
    <div
      style={{
        width: "100vw",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* 배경 박스 */}
      <div
        style={{
          width: 402,
          height: 874,
          position: "relative",
          backgroundColor: "#EEEEEE",
          overflow: "hidden",
        }}
      >
        {/* 노이즈 레이어 (연하게) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `url(${noise})`,
            backgroundSize: "cover",
            backgroundRepeat: "repeat",
            opacity: 0.25, // 노이즈만 연하게
            zIndex: 0,
          }}
        />

        {/* 로고 + 텍스트 (페이드인/아웃) */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0px",
            opacity: fade, // 로고+글씨만 페이드
            transition: "opacity 0.5s ease",
            zIndex: 1,
          }}
        >
          <img
            src={logo}
            alt="Logo"
            style={{
              width: 400,
              objectFit: "contain",
              display: "block",
            }}
          />
          <div
            style={{
              fontSize: 45,
              fontFamily: "Hakgyoansim_PosterOTFB",
              color: "#2E2E2E",
              fontWeight: 400,
              marginTop: "-80px",
            }}
          >
            영웅과 함께
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
