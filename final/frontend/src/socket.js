import { io } from "socket.io-client";

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? "http://127.0.0.1:8000";

const socket = io(SOCKET_URL, {
  path: "/ws/socket.io",
  withCredentials: true,
  transports: ["websocket"],
});

export default socket;



