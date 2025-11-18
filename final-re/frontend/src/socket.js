import { io } from "socket.io-client";

// 배포 환경에서는 VITE_SOCKET_URL 환경변수로 소켓 서버 주소를 주입하고,
// 환경변수가 없으면 Render 기본 URL(heroes-chat.onrender.com)을 사용합니다.
const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL ?? "https://heroes-chat.onrender.com";

const socket = io(SOCKET_URL, {
  path: "/ws/socket.io",
  withCredentials: true,
  transports: ["websocket"],
});

export default socket;



