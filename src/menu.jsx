import React, { useEffect, useState } from "react";
import peterface from "./fonts/peterface.png";
import buffettface from "./fonts/buffettface.png";
import woodface from "./fonts/woodface.png";
import back from "./fonts/back.png";
import personchatback_peter from "./fonts/personchatback_peter.png";
import personchatback_buf from "./fonts/personchatback_buf.png";
import personchatback_wood from "./fonts/personchatback_wood.png";
import "./App.css";
import { useNavigate } from "react-router-dom";

function Menu({ onBack }) {
  const navigate = useNavigate();

  // ✅ mentorData 정의
  const mentorData = {
    "피터 린치": {
      name: "피터 린치",
      img: peterface,
      background: personchatback_peter,
    },
    "워렌 버핏": {
      name: "워렌 버핏",
      img: buffettface,
      background: personchatback_buf,
    },
    "캐시 우드": {
      name: "캐시 우드",
      img: woodface,
      background: personchatback_wood,
    },
  };

// ✅ mentor 상태 초기값을 localStorage에서 불러오거나 기본값 설정
const [mentor, setMentor] = useState(() => {
  const saved = localStorage.getItem("assignedMentor");
  return saved && mentorData[saved] ? saved : "피터 린치";
});

useEffect(() => {
  // mentor 값이 바뀔 때마다 localStorage에 저장
  localStorage.setItem("assignedMentor", mentor);
}, [mentor]);

const current = mentorData[mentor];


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
          overflow: "hidden",
          backgroundImage: `url(${current.background})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        {/* ✅ 반투명 회색 오버레이 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "rgba(246, 246, 246, 0.9)",
          }}
        />

        {/* 상단 회색바 */}
        <div
          style={{
            width: 402,
            height: 60,
            left: 0,
            top: 0,
            position: "absolute",
            background: "#D9D9D9",
            zIndex: 2,
          }}
        />

        {/* 상단 흰색바 */}
        <div
          style={{
            width: 402,
            height: 55,
            left: -1,
            top: 60,
            position: "absolute",
            background: "white",
            boxShadow: "0px 4px 120px rgba(57, 86, 77, 0.15)",
            zIndex: 2,
          }}
        />

        {/* 뒤로가기 버튼 */}
        <img
          src={back}
          alt="뒤로가기"
          onClick={onBack}
          style={{
            width: 13,
            height: 10,
            position: "absolute",
            left: 17,
            top: 83,
            cursor: "pointer",
            zIndex: 3,
          }}
        />

        {/* 타이틀 */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            top: 76,
            textAlign: "center",
            color: "#27292E",
            fontSize: 16,
            fontFamily: "SF Pro",
            fontWeight: "700",
            lineHeight: "21.6px",
            zIndex: 3,
          }}
        >
          메뉴
        </div>

        {/* 프로필 */}
        <div
          style={{
            width: 80,
            height: 80,
            left: 161,
            top: 140,
            position: "absolute",
            background: "#dbdbdbff",
            borderRadius: 25,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 3,
            marginTop: 25,
          }}
        >
          <img
            src={current.img}
            alt={current.name}
            style={{
              width: 70,
              height: 70,
              borderRadius: "50%",
              objectFit: "cover",
              marginTop: 20,
            }}
          />
        </div>

        {/* 이름 */}
        <div
          style={{
            width: 107.61,
            height: 24.75,
            left: 146,
            top: 260,
            position: "absolute",
            textAlign: "center",
            color: "#27292E",
            fontSize: 16,
            fontFamily: "SF Pro",
            fontWeight: "700",
            lineHeight: "21.6px",
            zIndex: 3,
          }}
        >
          {current.name}
        </div>

        {/* 버튼 영역 */}
        <div
          style={{
            width: 323,
            left: 39,
            top: 315,
            position: "absolute",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "flex-end",
            gap: 36,
            display: "inline-flex",
            zIndex: 3,
          }}
        >
          {/* 버튼 1 */}
          <div
            onClick={() => alert("첫 번째 뉴스 정리본으로 이동")}
            style={{
              width: 322,
              height: 35.64,
              background: "#5BA1E9",
              borderRadius: 10,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginTop: 25,
            }}
          >
            <span
              style={{
                color: "black",
                fontSize: 16,
                fontWeight: "600",
                fontFamily: "SF Pro",
              }}
            >
              뉴스 정리본
            </span>
          </div>



          {/* 버튼 2: 영웅 바꾸기 */}
          <div
            onClick={() => navigate("/chooseper")}
            style={{
              width: 322,
              height: 35.64,
              background: "#014A97",
              borderRadius: 10,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                color: "white",
                fontSize: 16,
                fontWeight: "550",
                fontFamily: "SF Pro",
              }}
            >
              영웅 바꾸기
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Menu;
