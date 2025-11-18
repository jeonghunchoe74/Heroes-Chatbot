import React from "react";
import useViewportScale from "./useViewportScale";

const DESIGN_WIDTH = 402;
const DESIGN_HEIGHT = 874;

/**
 * PC에서 보이는 기준 비율(402 x 874)을 유지하면서
 * 모바일/태블릿 등 어떤 기기에서도 화면 전체에 맞게
 * 축소/확대되도록 감싸는 공통 레이아웃 컴포넌트.
 *
 * - 비율은 그대로 유지
 * - 기기 화면에 맞게 자동으로 스케일 조정
 * - 라우트가 바뀌어도 항상 같은 기준 캔버스를 유지
 */
export default function ScreenLayout({ children }) {
  const scale = useViewportScale(DESIGN_WIDTH, DESIGN_HEIGHT);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        overflow: "hidden",
        backgroundColor: "#f5f5f5",
      }}
    >
      <div
        style={{
          width: DESIGN_WIDTH,
          height: DESIGN_HEIGHT,
          transform: `scale(${scale})`,
          transformOrigin: "top center",
          position: "relative",
          overflow: "hidden",
          backgroundColor: "#ffffff",
        }}
      >
        <div
          style={{
            position: "relative",
            width: "100%",
            height: "100%",
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}


