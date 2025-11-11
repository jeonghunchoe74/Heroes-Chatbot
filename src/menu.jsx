import React from "react";
import peterface from "./fonts/peterface.png";
import back from "./fonts/back.png";
import personchatback from "./fonts/personchatback_peter.png";
import "./App.css";

function Menu({ onBack, onChangeHero }) {
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
            backgroundImage: `url(${personchatback})`,
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

        {/* 프로필 영역 */}
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
            }}
        >
            <img
            src={peterface}
            alt="peterface"
            style={{
                width: 110,
                height: 110,
                borderRadius: "50%",
                objectFit: "cover",
            }}
            />
        </div>

        {/* 이름 */}
        <div
            style={{
            width: 107.61,
            height: 24.75,
            left: 146,
            top: 240,
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
            피터 린치
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
            }}
            >
            <span
                style={{
                color: "black",
                fontSize: 16,
                fontWeight: "500",
                fontFamily: "SF Pro",
                }}
            >
                뉴스 정리본 1
            </span>
            </div>

            {/* 버튼 2 */}
            <div
            onClick={() => alert("두 번째 뉴스 정리본으로 이동")}
            style={{
                width: 322,
                height: 35.64,
                background: "#5BA1E9",
                borderRadius: 10,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
            >
            <span
                style={{
                color: "black",
                fontSize: 16,
                fontWeight: "500",
                fontFamily: "SF Pro",
                }}
            >
                뉴스 정리본 2
            </span>
            </div>

            {/* 버튼 3 — 영웅 바꾸기 */}
            <div
            onClick={onChangeHero} // ✅ ChoosePer.jsx로 이동하도록 변경
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
                fontWeight: "500",
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