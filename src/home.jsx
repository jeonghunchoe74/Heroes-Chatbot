import React from "react";
import { useNavigate } from "react-router-dom";
import noise from "./fonts/noise.png"; // ✅ 노이즈 이미지 임포트

function Home() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        width: "100vw",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* ✅ 노이즈 배경 포함한 컨테이너 */}
      <div
        style={{
          width: 402,
          height: 874,
          position: "relative",
          backgroundColor: "#EEEEEE",
          overflow: "hidden",
        }}
      >
        {/* ✅ 노이즈 배경 레이어 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `url(${noise})`,
            backgroundSize: "cover",
            backgroundRepeat: "repeat",
            opacity: 0.3, // 💡 노이즈 선명도 조절 (0.2~0.5 사이 조절 가능)
            zIndex: 0,
          }}
        ></div>

        {/* ✅ 기존 콘텐츠 레이어 (노이즈 위로 올라옴) */}
        <div style={{ position: "relative", zIndex: 1 }}>
          {/* 상단 문구 */}
          <div
            style={{
              left: 136,
              top: 168,
              position: "absolute",
              textAlign: "center",
              color: "#2E2E2E",
              fontSize: 16,
              fontFamily: "SF Pro",
              fontWeight: 700,
            }}
          >
            투자를 시작하세요!
          </div>

          {/* 메인 타이틀 */}
          <div
            style={{
              width: 259,
              left: 71,
              top: 117,
              position: "absolute",
              textAlign: "center",
              color: "#2E2E2E",
              fontSize: 36,
              fontFamily: "Hakgyoansim_PosterOTFB",
              fontWeight: 400,
            }}
          >
            영웅과 함께
          </div>

          {/* 안내 문구 */}
          <div
            style={{
              width: 314,
              left: 44,
              top: 275,
              position: "absolute",
              textAlign: "center",
              color: "#2E2E2E",
              fontSize: 15,
              fontFamily: "SF Pro",
              fontWeight: 700,
              lineHeight: "25px",
            }}
          >
            당신에게 맞는 투자 여정을 선택해보세요.
          </div>

          {/* 큰 테두리 박스 */}
          <div
            style={{
              width: 320,
              height: 300,
              left: 41,
              top: 320,
              position: "absolute",
              border: "2px solid black",
              background: "transparent",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            {/* 내부 작은 박스 */}
            <div
              style={{
                width: 310,
                height: 250,
                border: "1px solid black",
                background: "transparent",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "20px 0",
                position: "relative",
              }}
            >
              {/* 🌱 영웅의 멘토링 */}
              <div
                onClick={() => navigate("/test")}
                style={{
                  width: 260,
                  height: 100,
                  background: "rgba(247, 199, 96, 0.15)",
                  border: "1px solid #C13A00",
                  borderRadius: 0,
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    fontSize: 16,
                    fontFamily: "Hakgyoansim_PosterOTFB",
                    color: "#2E2E2E",
                    marginBottom: "8px",
                  }}
                >
                  🌱 영웅의 멘토링
                </div>
                <div
                  style={{
                    color: "black",
                    fontSize: 9,
                    fontFamily: "SF Pro",
                    fontWeight: 500,
                    lineHeight: "18px",
                    textAlign: "center",
                    marginTop: "5px",
                  }}
                >
                  나의 투자 성향을 알아보고
                  <br />
                  나만의 영웅과 함께 투자 방향을 잡아보세요.
                </div>
              </div>

              {/* 구분선 */}
              <div
                style={{
                  width: "85%",
                  height: "1px",
                  backgroundColor: "#afafaf",
                  opacity: 0.4,
                  margin: "6px 0",
                }}
              ></div>

              {/* 📖 영웅과 스터디 */}
              <div
                onClick={() => navigate("/choose-men")}
                style={{
                  width: 260,
                  height: 100,
                  background: "rgba(117, 216, 120, 0.16)",
                  border: "1px solid #085D05",
                  borderRadius: 0,
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    fontSize: 16,
                    fontFamily: "Hakgyoansim_PosterOTFB",
                    color: "#2E2E2E",
                    marginBottom: "8px",
                  }}
                >
                  📖 영웅과 스터디
                </div>
                <div
                  style={{
                    color: "black",
                    fontSize: 9,
                    fontFamily: "SF Pro",
                    fontWeight: 500,
                    lineHeight: "18px",
                    textAlign: "center",
                    marginTop: "5px",
                  }}
                >
                  영웅과 함께 종목을 공부하고
                  <br />
                  뉴스와 자료를 함께 보며 투자 감각을 키워보세요.
                </div>
              </div>
            </div>
          </div>

          {/* 하단 마이페이지 */}
          <div
            onClick={() => navigate("/mypage")}
            style={{
              width: 320,
              height: 37,
              left: "50%",
              top: 710,
              position: "absolute",
              background: "rgba(183, 103, 71, 0.1)",
              border: "1px solid #B76747",
              transform: "translateX(-50%)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 15,
              fontFamily: "SF Pro",
              fontWeight: 590,
              color: "rgba(183, 103, 71, 0.95)",
            }}
          >
            마이페이지
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
