import { useEffect, useState } from "react";

/**
 * 디자인 기준 해상도(DESIGN_WIDTH x DESIGN_HEIGHT)를
 * 실제 뷰포트 크기에 맞춰 비율을 유지한 채로 스케일링하기 위한 훅.
 *
 * 예) 기준 해상도 402 x 874 기준으로, 기기 화면에 맞게 전체 화면을 축소/확대.
 */
export default function useViewportScale(
  designWidth = 402,
  designHeight = 874
) {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const updateScale = () => {
      if (typeof window === "undefined") {
        setScale(1);
        return;
      }

      const vw = window.innerWidth;
      const vh = window.innerHeight;
      if (!vw || !vh) {
        setScale(1);
        return;
      }

      const scaleX = vw / designWidth;
      const scaleY = vh / designHeight;
      const nextScale = Math.min(scaleX, scaleY);
      setScale(nextScale);
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, [designWidth, designHeight]);

  return scale;
}


