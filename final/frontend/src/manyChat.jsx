import { useEffect, useRef, useState } from "react";
import "./App.css";
import socket from "./socket";
import personchatback from "./fonts/manyback.png";
import profile from "./fonts/profile.png";
import send1 from "./fonts/send1.png";
import send2 from "./fonts/send2.png";
import send3 from "./fonts/send3.png";
import peterface from "./fonts/peterface.png";
import buffettface from "./fonts/buffettface.png";
import woodface from "./fonts/woodface.png";

const URL_REGEX =
  /((?:https?:\/\/|www\d{0,3}[.]|[a-z0-9.-]+\.[a-z]{2,})(?:[^\s<>()"]*)?)/gi;

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const SHOW_DEMO = false;

const stockOptions = ["삼성전자", "POSCO홀딩스", "현대차", "카카오", "NAVER"];

const escapeHtml = (input = "") =>
  String(input)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const absUrl = (url) => {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  if (url.startsWith("/")) return `${API_BASE}${url}`;
  return `http://${url}`;
};

const linkify = (text) => {
  if (typeof text !== "string" || !text.trim()) return escapeHtml(text || "");
  let result = "";
  let lastIndex = 0;
  let match;
  URL_REGEX.lastIndex = 0;
  while ((match = URL_REGEX.exec(text)) !== null) {
    const url = match[1];
    const start = match.index;
    if (start > lastIndex) {
      result += escapeHtml(text.slice(lastIndex, start));
    }
    const href = url.toLowerCase().startsWith("http") ? url : `http://${url}`;
    const safeHref = escapeHtml(href);
    const safeLabel = escapeHtml(url);
    result += `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${safeLabel}</a>`;
    lastIndex = start + url.length;
  }
  if (lastIndex < text.length) {
    result += escapeHtml(text.slice(lastIndex));
  }
  return result;
};

const prettySize = (bytes) => {
  if (bytes === null || bytes === undefined) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex ? 1 : 0)} ${units[unitIndex]}`;
};

const iconByMime = (mime = "", name = "") => {
  const ext = (name.split(".").pop() || "").toLowerCase();
  if (mime.includes("pdf") || ext === "pdf") return "📄 PDF";
  if (["xls", "xlsx", "csv"].includes(ext)) return "📊 스프레드시트";
  if (["hwp", "hwpx"].includes(ext)) return "📝 한글 문서";
  if (mime.startsWith("image/")) return "🖼 이미지";
  if (mime.startsWith("text/")) return "📄 텍스트";
  return "📎 파일";
};

const isPdf = (meta) => {
  if (!meta) return false;
  const type = meta.mime || meta.type || "";
  const name = meta.name || "";
  return type.includes("pdf") || name.toLowerCase().endsWith(".pdf");
};

const isAnalyzable = (entry) => {
  if (!entry) return false;
  if (entry.type === "preview") return Boolean(entry.meta?.url);
  if (entry.type === "file") return isPdf(entry.meta?.file);
  return false;
};

function JoinScreen({
  room,
  guruLabel,
  showNameModal,
  tempName,
  setTempName,
  onOpenNameModal,
  onConfirmName,
  onCloseName,
}) {
  return (
    <div
      style={{
        width: 402,
        height: 874,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        background: "#fff",
        position: "relative",
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 700 }}>방 참가</div>
      <div style={{ fontSize: 14, color: "#333" }}>
        선택된 주식: <strong>{room || "미선택"}</strong>
      </div>
      <div style={{ fontSize: 14, color: "#333" }}>
        선택된 영웅: <strong>{guruLabel || "피터 린치"}</strong>
      </div>
      <button
        type="button"
        onClick={onOpenNameModal}
        style={{
          width: 260,
          height: 42,
          border: "none",
          borderRadius: 10,
          background: "#4FA3F7",
          color: "#fff",
          fontWeight: 700,
          cursor: "pointer",
          marginTop: 4,
        }}
      >
        방 참가하기
      </button>

      {showNameModal && (
        <>
          <div
            onClick={onCloseName}
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(0,0,0,0.35)",
            }}
          />
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: "absolute",
              width: 300,
              background: "#fff",
              borderRadius: 12,
              boxShadow: "0 6px 24px rgba(0,0,0,0.18)",
              padding: 16,
              zIndex: 2,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 15, color: "#333" }}>
              닉네임 입력
            </div>
            <input
              autoFocus
              type="text"
              value={tempName}
              onChange={(e) => setTempName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onConfirmName();
              }}
              placeholder="닉네임을 입력하세요"
              style={{
                width: "100%",
                height: 38,
                borderRadius: 10,
                border: "1px solid #ccc",
                padding: "0 10px",
                fontSize: 13,
              }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={onCloseName}
                style={{
                  border: "1px solid #ddd",
                  background: "#fff",
                  color: "#333",
                  borderRadius: 8,
                  padding: "6px 12px",
                  cursor: "pointer",
                }}
              >
                취소
              </button>
              <button
                type="button"
                onClick={onConfirmName}
                style={{
                  border: "none",
                  background: "#4FA3F7",
                  color: "#fff",
                  borderRadius: 8,
                  padding: "6px 12px",
                  cursor: "pointer",
                }}
              >
                입장
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function App() {
  const [msgs, setMsgs] = useState([]);
  const [myId, setMyId] = useState(null);
  const [selectedGuru, setSelectedGuru] = useState(
    localStorage.getItem("selectedGuru") || "lynch"
  );
  const [currentGuru, setCurrentGuru] = useState("lynch");
  const [mentorEnabled, setMentorEnabled] = useState(true);
  const [count, setCount] = useState(null);

  const [inputText, setInputText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetData, setSheetData] = useState(null);
  const [sheetDragging, setSheetDragging] = useState(false);
  const [sheetDragY, setSheetDragY] = useState(0);
  const [sheetAnswer, setSheetAnswer] = useState("");
  // 바텀시트 스레드용 로컬 뷰 메시지
  const [sheetThreadMsgs, setSheetThreadMsgs] = useState([]);
  const [joined, setJoined] = useState(false);
  const [displayName, setDisplayName] = useState(
    localStorage.getItem("displayName") || ""
  );
  const [room, setRoom] = useState(localStorage.getItem("room") || "삼성전자");
  const [showNameModal, setShowNameModal] = useState(false);
  const [tempName, setTempName] = useState(localStorage.getItem("displayName") || "");

  const fileInputRef = useRef(null);
  const endRef = useRef(null);
  const dragStartYRef = useRef(0);
  const sheetDragYRef = useRef(0);
  const bodyOverflowRef = useRef("");

  // (중복 정의 방지) 유틸/시트 제스처는 아래 구간의 기존 정의를 사용합니다.

  const mentors = SHOW_DEMO
    ? [
        {
          name: "이다후",
          color: "#F7C948",
          message: "www.apple.com",
        },
        {
          name: "윤철진",
          color: "#8E7CC3",
          message: "혁신 기술은 단기 변동보다 미래의 성장을 만든다고 믿어.",
        },
        {
          name: "최정훈",
          color: "#4FA3F7",
          message: "일상에서 소비되는 브랜드 속에 투자 기회가 숨어 있지.",
        },
      ]
    : [];

  useEffect(() => {
    const onConnect = () => {
      setMyId(socket.id);
      if (joined) {
        const storedName =
          (localStorage.getItem("displayName") || displayName || "익명").trim() ||
          "익명";
        const storedRoom = localStorage.getItem("room") || room || "삼성전자";
        socket.emit("join_room", { room: storedRoom, name: storedName });
      }
    };
    const onSystem = (msg) =>
      setMsgs((prev) => [...prev, { type: "system", msg }]);
    const onChat = (payload = {}) => {
      const entryType = payload.type || "chat";
      const msg = payload.msg || payload;
      setMsgs((prev) => [...prev, { type: entryType, msg }]);
    };
    const onPreview = (msg) =>
      setMsgs((prev) => {
        try {
          const url = (msg && msg.url) || "";
          let ownerSid = "";
          let ownerName = "";
          if (url) {
            for (let i = prev.length - 1; i >= 0; i -= 1) {
              const entry = prev[i];
              if (entry?.type === "chat") {
                const text = entry.msg?.text || "";
                if (text && text.includes(url)) {
                  ownerSid = entry.msg?.sender?.sid || "";
                  ownerName = entry.msg?.sender?.name || "";
                  break;
                }
              }
            }
          }
          const enriched = ownerSid
            ? { ...msg, ownerSid, ownerName }
            : msg;
          return [...prev, { type: "preview", msg: enriched }];
        } catch (e) {
          return [...prev, { type: "preview", msg }];
        }
      });
    const onFile = (payload = {}) => {
      const entryType = payload.type || "file";   // 혹시 모를 확장 대비
      const msg = payload.msg || payload;         // 안쪽 msg만 꺼내기
      setMsgs((prev) => [...prev, { type: entryType, msg }]);
    };
    const onGuru = (payload = {}) =>
      setCurrentGuru(payload.guruId || payload.id || "lynch");
    const onMentor = (payload = {}) =>
      setMentorEnabled(
        typeof payload.enabled === "boolean" ? payload.enabled : !!payload
      );
    const onStats = (payload = {}) =>
      setCount(
        typeof payload.count === "number" ? payload.count : Number(payload) || null
      );

    socket.on("connect", onConnect);
    socket.on("system", onSystem);
    socket.on("chat_message", onChat);
    socket.on("link_preview", onPreview);
    socket.on("file_shared", onFile);
    socket.on("room_guru_changed", onGuru);
    socket.on("mentor_enabled_changed", onMentor);
    socket.on("lobby_stats", onStats);

    return () => {
      socket.off("connect", onConnect);
      socket.off("system", onSystem);
      socket.off("chat_message", onChat);
      socket.off("link_preview", onPreview);
      socket.off("file_shared", onFile);
      socket.off("room_guru_changed", onGuru);
      socket.off("mentor_enabled_changed", onMentor);
      socket.off("lobby_stats", onStats);
    };
  }, [joined, room, displayName]);

  useEffect(() => {
    const saved = localStorage.getItem("displayName");
    if (saved) {
      setDisplayName(saved);
    }
  }, []);

  // 선택 화면을 거치지 않고 진입 시 자동 참가
  useEffect(() => {
    if (joined) return;
    const n = ((localStorage.getItem("displayName") || displayName) || "").trim();
    const r = (localStorage.getItem("room") || room || "").trim();
    const g = (localStorage.getItem("selectedGuru") || selectedGuru || "lynch").trim();
    if (n && r) {
      setDisplayName(n);
      setRoom(r);
      setSelectedGuru(g);
      socket.emit("join_room", { room: r, name: n });
      socket.emit("set_room_guru", { guruId: g, room: r });
      setJoined(true);
    }
  }, [joined, displayName, room, selectedGuru]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  useEffect(() => {
    if (sheetOpen) {
      bodyOverflowRef.current = document.body.style.overflow;
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = bodyOverflowRef.current || "";
    }
  }, [sheetOpen]);

  useEffect(() => {
    return () => {
      document.body.style.overflow = bodyOverflowRef.current || "";
      window.removeEventListener("pointermove", onSheetPointerMove);
      window.removeEventListener("pointerup", onSheetPointerUp);
      window.removeEventListener("pointercancel", onSheetPointerUp);
    };
  }, []);

  const send = (text) => {
    const trimmed = (text || "").trim();
    if (!trimmed) return;
    socket.emit("chat_message", { message: trimmed, room });
    setInputText("");
  };

  const onJoin = () => {
    const n = (displayName || "").trim();
    if (!n) {
      alert("이름을 입력하세요.");
      return;
    }
    if (!room) {
      alert("방(주식)을 선택하세요.");
      return;
    }

    localStorage.setItem("displayName", n);
    localStorage.setItem("room", room);
    localStorage.setItem("selectedGuru", selectedGuru);
    setDisplayName(n);

    socket.emit("join_room", { room, name: n });
    socket.emit("set_room_guru", { guruId: selectedGuru, room });
    setJoined(true);
  };

  const onConfirmName = () => {
    const n = (tempName || "").trim();
    if (!n) {
      alert("닉네임을 입력하세요.");
      return;
    }
    if (!room) {
      alert("방(주식)을 선택하세요.");
      return;
    }
    try {
      localStorage.setItem("displayName", n);
      localStorage.setItem("room", room);
      localStorage.setItem("selectedGuru", selectedGuru);
    } catch {}
    setDisplayName(n);
    socket.emit("join_room", { room, name: n });
    socket.emit("set_room_guru", { guruId: selectedGuru, room });
    setShowNameModal(false);
    setJoined(true);
  };

  const uploadFile = async (file) => {
    if (!socket.id) {
      setMsgs((prev) => [
        ...prev,
        { type: "system", msg: { text: `연결되지 않았습니다. 잠시 후 다시 시도해주세요.` } },
      ]);
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("user", displayName || "익명");
    form.append("sid", socket.id);
    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        throw new Error(`업로드 실패 (${res.status})`);
      }
      await res.json();
    } catch (error) {
      setMsgs((prev) => [
        ...prev,
        { type: "system", msg: { text: `파일 업로드 실패: ${file.name}` } },
      ]);
    }
  };

  const handleFiles = async (files) => {
    if (!files?.length) return;
    for (const file of files) {
      await uploadFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const onDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const files = event.dataTransfer?.files;
    if (files && files.length) {
      handleFiles(Array.from(files));
    }
  };

  const onDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  const OPEN_TRANSITION =
    "transform 0.2s cubic-bezier(.2,.8,.2,1), opacity 0.35s ease";
  const CLOSE_TRANSITION =
    "transform 0.4s cubic-bezier(.2,.8,.2,1), opacity 0.45s ease";

  const openAnalyze = (entry) => {
    if (!isAnalyzable(entry)) return;
    const key = getSheetThreadKey(entry);
    
    if (sheetOpen) {
      setSheetData(entry);
      // 스레드 메시지 초기화 (서버 히스토리 로드 전 임시)
      setSheetThreadMsgs([]);
      try {
        if (key) {
          socket.emit("thread_open", {
            type: entry.type,
            threadKey: key,
            meta: entry.meta || {},
          });
        }
      } catch {}
      return;
    }
    setSheetData(entry);
    // 스레드 메시지 초기화 (서버 히스토리 로드 전 임시)
    setSheetThreadMsgs([]);
    requestAnimationFrame(() => {
      setSheetOpen(true);
    });
    try {
      if (key) {
        socket.emit("thread_open", {
          type: entry.type,
          threadKey: key,
          meta: entry.meta || {},
        });
      }
    } catch {}
  };

  const closeSheet = () => {
    setSheetOpen(false);
    setSheetDragging(false);
    setSheetDragY(0);
    sheetDragYRef.current = 0;
    setTimeout(() => setSheetData(null), 250);
  };

  const onSheetPointerDown = (event) => {
    if (!sheetOpen) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    const y =
      event.clientY ?? (event.touches && event.touches[0]?.clientY) ?? 0;
    dragStartYRef.current = y;
    setSheetDragging(true);
    setSheetDragY(0);
    sheetDragYRef.current = 0;

    window.addEventListener("pointermove", onSheetPointerMove);
    window.addEventListener("pointerup", onSheetPointerUp);
    window.addEventListener("pointercancel", onSheetPointerUp);
  };

  function onSheetPointerMove(event) {
    const y = event.clientY ?? 0;
    const delta = Math.max(0, y - dragStartYRef.current);
    setSheetDragY(delta);
    sheetDragYRef.current = delta;
  }

  function onSheetPointerUp() {
    window.removeEventListener("pointermove", onSheetPointerMove);
    window.removeEventListener("pointerup", onSheetPointerUp);
    window.removeEventListener("pointercancel", onSheetPointerUp);

    const CLOSE_THRESHOLD = 120;
    const shouldClose = sheetDragYRef.current > CLOSE_THRESHOLD;
    setSheetDragging(false);
    setSheetDragY(0);
    sheetDragYRef.current = 0;
    if (shouldClose) {
      closeSheet();
    }
  }

  // 스레드 키 생성: 미디어마다 고유
  const getSheetThreadKey = (data) => {
    if (!data) return "";
    if (data.type === "file") {
      const fid = data.meta?.file?.id || data.meta?.file?.url || data.meta?.file?.name;
      return fid ? `thread:file:${fid}` : "";
    }
    if (data.type === "preview") {
      const url = data.meta?.url || data.meta?.title;
      return url ? `thread:url:${url}` : "";
    }
    return "";
  };

  // 바텀시트 열릴 때 현재 msgs에서 스레드 메시지 추출 (서버 히스토리가 없을 때만 사용)
  const initSheetThread = (data) => {
    const key = getSheetThreadKey(data);
    if (!key) {
      setSheetThreadMsgs([]);
      return;
    }
    // 서버 히스토리를 기다리는 동안 로컬 메시지만 표시 (히스토리가 오면 덮어씌워짐)
    const filtered = (msgs || []).filter((m) => {
      const text = m?.msg?.text || "";
      return typeof text === "string" && text.includes(`[${key}]`);
    });
    // 서버 히스토리가 아직 없을 때만 로컬 메시지 사용
    if (filtered.length > 0) {
      setSheetThreadMsgs(filtered);
    }
  };

  // 서버 스레드 이벤트 수신
  useEffect(() => {
    const onThreadMessage = (payload = {}) => {
      const msg = payload.msg || payload;
      const threadKey = msg.threadKey || "";
      const currentKey = getSheetThreadKey(sheetData);
      if (!threadKey || !currentKey || threadKey !== currentKey) return;
      // 새 메시지 추가
      setSheetThreadMsgs((prev) => {
        // 중복 방지: 같은 ts나 text를 가진 메시지가 이미 있으면 추가하지 않음
        const exists = prev.some((p) => {
          const pMsg = p.msg || {};
          const pTs = pMsg.ts || pMsg.ts;
          const pText = pMsg.text || "";
          const mTs = msg.ts;
          const mText = msg.text || "";
          return pTs === mTs && pText === mText;
        });
        if (exists) return prev;
        return [...prev, { type: "thread", msg }];
      });
    };
    const onThreadHistory = (payload = {}) => {
      const threadKey = payload.threadKey || "";
      const currentKey = getSheetThreadKey(sheetData);
      if (!threadKey || !currentKey || threadKey !== currentKey) return;
      // 서버에서 받은 히스토리로 완전히 교체 (개별 스레드별로 저장된 대화)
      const messages = Array.isArray(payload.messages) ? payload.messages : [];
      setSheetThreadMsgs(messages.map((m) => ({ type: "thread", msg: m })));
    };
    socket.on("thread_message", onThreadMessage);
    socket.on("thread_history", onThreadHistory);
    return () => {
      socket.off("thread_message", onThreadMessage);
      socket.off("thread_history", onThreadHistory);
    };
  }, [sheetData]);

  // 바텀시트에서 메시지 전송 (업로더만)
  const sendSheetMessage = () => {
    const text = (sheetAnswer || "").trim();
    if (!text) return;
    const key = getSheetThreadKey(sheetData);
    if (!key) return;
    socket.emit("thread_message", { threadKey: key, text });
    setSheetAnswer("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(inputText);
    }
  };

  const initial = (text) => (text?.[0] || "?").toUpperCase();
  const time = (ts) => {
    const d = ts ? new Date(Number(ts)) : new Date();
    if (Number.isNaN(d.getTime())) return "";
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
  };

  const renderSystem = (entry, index) => {
    const text =
      typeof entry.msg === "string" ? entry.msg : entry.msg?.text || "";
    return (
      <div
        key={`sys-${index}`}
        style={{
          textAlign: "center",
          fontSize: 11,
          color: "#555",
          marginTop: 12,
        }}
      >
        {text}
      </div>
    );
  };

  const renderChat = (entry, index) => {
    const msg = entry.msg || {};
    const currentSocketId = socket.id || myId;
    const messageSid = msg.sender?.sid ?? msg.sid;
    const messageName = msg.sender?.name ?? msg.name;
    const isMe = Boolean(
      (currentSocketId && messageSid && messageSid !== "ai" && messageSid === currentSocketId) ||
      (!messageSid && messageName && messageName === (displayName || localStorage.getItem("displayName")))
    );
    const isAI = msg.sender?.sid === "ai";
    const senderColor = getGuruColor(currentGuru, "profileBackground");
    const displayName = isAI 
      ? (guruLabels[currentGuru] || "피터 린치")
      : (msg.sender?.name || "멘토");
    const time = msg.ts
      ? new Date(msg.ts).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";

    if (isMe) {
      return (
        <div
          key={`chat-${index}`}
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginTop: 10,
            paddingRight: 14,
          }}
        >
          <div
            style={{
              background: "#fbeb56ff",
              borderRadius: 12,
              borderTopRightRadius: 0,
              padding: "10px 14px",
              maxWidth: 250,
              fontSize: 12,
              lineHeight: "18px",
              position: "relative",
              wordBreak: "break-word",
              overflowWrap: "break-word",
            }}
          >
            <div
              style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", overflowWrap: "break-word" }}
              dangerouslySetInnerHTML={{ __html: linkify(msg.text || "") }}
            />
            {time && (
              <div
                style={{
                  fontSize: 10,
                  color: "#666",
                  textAlign: "right",
                  marginTop: 4,
                }}
              >
                {time}
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        key={`chat-${index}`}
        style={{ display: "flex", flexDirection: "column", marginTop: 12 }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            paddingLeft: 12,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              overflow: "hidden",
              transform: "translateY(3px)",
              background: senderColor,
            }}
          >
            <img
              src={getGuruFace(currentGuru)}
              alt="guru"
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
          <div
            style={{
              fontWeight: 700,
              fontSize: 12,
              color: "#333",
              marginTop: 2,
            }}
          >
            {displayName}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            paddingLeft: 52,
          }}
        >
          <div
            style={{
              background: "#F9F9F9",
              borderRadius: 12,
              borderTopLeftRadius: 0,
              padding: "10px 14px",
              maxWidth: 260,
              fontSize: 12,
              lineHeight: "18px",
              textAlign: "left",
              boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
              transform: "translateY(-4px)",
              wordBreak: "break-word",
              overflowWrap: "break-word",
            }}
          >
            <div
              style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", overflowWrap: "break-word" }}
              dangerouslySetInnerHTML={{ __html: linkify(msg.text || "") }}
            />
            {time && (
              <div
                style={{
                  fontSize: 10,
                  color: "#777",
                  marginTop: 6,
                  textAlign: "right",
                }}
              >
                {time}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderPreview = (entry, index) => {
    const preview = entry.msg || {};
    const actions = (
      <div
        style={{
          marginTop: 12,
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <button
          type="button"
          onClick={() => openAnalyze({ type: "preview", meta: preview })}
          style={{
            border: "none",
            background: getGuruColor(currentGuru, "analyzeButton"),
            color: "#fff",
            borderRadius: 10,
            padding: "6px 12px",
            fontSize: 11,
            cursor: "pointer",
          }}
        >
          분석하기
        </button>
        <a
          href={absUrl(preview.url)}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            border: "none",
            background: "#E0E0E0",
            color: "#333",
            borderRadius: 10,
            padding: "6px 12px",
            fontSize: 11,
            textDecoration: "none",
          }}
        >
          원문 열기
        </a>
      </div>
    );

    return (
      <div
        key={`preview-${index}`}
        style={{
          marginTop: 12,
          paddingLeft: 52,
        }}
      >
        <div
          style={{
            background: "#ffffff",
            borderRadius: 14,
            padding: "12px 14px",
            boxShadow: "0px 2px 8px rgba(0,0,0,0.08)",
            maxWidth: 280,
          }}
        >
          {preview.image && (
            <div
              style={{
                width: "100%",
                height: 140,
                borderRadius: 12,
                overflow: "hidden",
                marginBottom: 12,
                background: "#f5f5f5",
              }}
            >
              <img
                src={preview.image}
                alt={preview.title || "preview"}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </div>
          )}
          <div
            style={{
              fontWeight: 700,
              fontSize: 13,
              marginBottom: 8,
              color: "#333",
            }}
          >
            {preview.title || preview.site_name || preview.url}
          </div>
          {preview.description && (
            <div style={{ fontSize: 12, color: "#555", lineHeight: "18px" }}>
              {preview.description}
            </div>
          )}
          {actions}
        </div>
      </div>
    );
  };

  const renderFile = (entry, index) => {
    const sender = entry.msg?.sender ?? {};
    const file = entry.msg?.file ?? {};
    // sender.sid가 "http"가 아니고, socket.id와 일치하면 내가 보낸 것
    const currentSocketId = socket.id || myId; // socket.id가 없으면 state fallback
    const isMe = Boolean(
      currentSocketId && 
      sender.sid && 
      sender.sid !== "http" && 
      sender.sid === currentSocketId
    );
    const key = entry.msg?.id ?? `file-${file.id ?? index}`;
    const timeStr = time(entry.msg?.ts);

    if (isMe) {
      return (
        <div
          key={key}
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginTop: 10,
            paddingRight: 14,
          }}
        >
          <div
            style={{
              background: "#fbeb56ff",
              borderRadius: 12,
              borderTopRightRadius: 0,
              padding: "10px 14px",
              maxWidth: 250,
              fontSize: 12,
              lineHeight: "18px",
              position: "relative",
            }}
          >
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 14, marginBottom: 6 }}>
                📄 PDF
              </div>
              <a
                href={absUrl(file.url)}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#333",
                  textDecoration: "none",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 13,
                  display: "block",
                  wordBreak: "break-word",
                }}
                onMouseEnter={(e) => {
                  e.target.style.textDecoration = "underline";
                  e.target.style.color = "#4FA3F7";
                }}
                onMouseLeave={(e) => {
                  e.target.style.textDecoration = "none";
                  e.target.style.color = "#333";
                }}
              >
                {file.name}
              </a>
            </div>
            <div style={{ fontSize: 11, color: "#777", marginBottom: 8 }}>
              {prettySize(file.size)} · {file.mime || "파일"}
            </div>
            {entry.msg?.summary && (
              <div style={{ 
                fontSize: 12, 
                color: "#444", 
                lineHeight: "18px",
                marginBottom: 8,
                maxHeight: "4.5em",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}>
                {entry.msg.summary}
              </div>
            )}
            {isPdf(file) && (
              <div style={{ marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => openAnalyze({
                    type: "file",
                    meta: {
                      file: file,
                      preview: entry.msg?.preview,
                      ownerSid: sender.sid,
                      ownerName: sender.name,
                    }
                  })}
                  style={{
                    border: "none",
                    background: getGuruColor(currentGuru, "analyzeButton"),
                    color: "#fff",
                    borderRadius: 10,
                    padding: "6px 12px",
                    fontSize: 11,
                    cursor: "pointer",
                  }}
                >
                  분석하기
                </button>
              </div>
            )}
            {timeStr && (
              <div
                style={{
                  fontSize: 10,
                  color: "#666",
                  textAlign: "right",
                  marginTop: 4,
                }}
              >
                {timeStr}
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        key={key}
        style={{ display: "flex", flexDirection: "column", marginTop: 12 }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            paddingLeft: 12,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              overflow: "hidden",
              transform: "translateY(3px)",
              background: getGuruColor(currentGuru, "profileBackground"),
            }}
          >
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              {initial(sender.name)}
            </div>
          </div>
          <div
            style={{
              fontWeight: 700,
              fontSize: 12,
              color: "#333",
              marginTop: 2,
            }}
          >
            {sender.name || "사용자"}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            paddingLeft: 52,
          }}
        >
          <div
            style={{
              background: "#F9F9F9",
              borderRadius: 12,
              borderTopLeftRadius: 0,
              padding: "10px 14px",
              maxWidth: 260,
              fontSize: 12,
              lineHeight: "18px",
              textAlign: "left",
              boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
              transform: "translateY(-4px)",
            }}
          >
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 14, marginBottom: 6 }}>
                📄 PDF
              </div>
              <a
                href={absUrl(file.url)}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#333",
                  textDecoration: "none",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 13,
                  display: "block",
                  wordBreak: "break-word",
                }}
                onMouseEnter={(e) => {
                  e.target.style.textDecoration = "underline";
                  e.target.style.color = "#4FA3F7";
                }}
                onMouseLeave={(e) => {
                  e.target.style.textDecoration = "none";
                  e.target.style.color = "#333";
                }}
              >
                {file.name}
              </a>
            </div>
            <div style={{ fontSize: 11, color: "#777", marginBottom: 8 }}>
              {prettySize(file.size)} · {file.mime || "파일"}
            </div>
            {entry.msg?.summary && (
              <div style={{ 
                fontSize: 12, 
                color: "#444", 
                lineHeight: "18px",
                marginBottom: 8,
                maxHeight: "4.5em",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}>
                {entry.msg.summary}
              </div>
            )}
            {isPdf(file) && (
              <div style={{ marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => openAnalyze({
                    type: "file",
                    meta: {
                      file: file,
                      preview: entry.msg?.preview,
                      ownerSid: sender.sid,
                      ownerName: sender.name,
                    }
                  })}
                  style={{
                    border: "none",
                    background: getGuruColor(currentGuru, "analyzeButton"),
                    color: "#fff",
                    borderRadius: 10,
                    padding: "6px 12px",
                    fontSize: 11,
                    cursor: "pointer",
                  }}
                >
                  분석하기
                </button>
              </div>
            )}
            {timeStr && (
              <div
                style={{
                  fontSize: 10,
                  color: "#777",
                  marginTop: 6,
                  textAlign: "right",
                }}
              >
                {timeStr}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const guruLabels = {
    lynch: "피터 린치",
    buffett: "워렌 버핏",
    ark: "캐시 우드",
  };

  const guruFaces = {
    lynch: peterface,
    buffett: buffettface,
    ark: woodface,
  };

  const getGuruFace = (guruId) => {
    return guruFaces[guruId] || peterface;
  };

  // 멘토별 색상 테마
  const guruColors = {
    buffett: {
      analyzeButton: "#8DC70D",
      popupBackground: "#eaf1e7ff",
      profileBackground: "#6ca354ff",
    },
    ark: {
      analyzeButton: "#ca726fff",
      popupBackground: "#f7f2f2ff",
      profileBackground: "#cea1a1ff",
    },
    lynch: {
      analyzeButton: "#4FA3F7",
      popupBackground: "#f1f9ffff",
      profileBackground: "#5353b0ff",
    },
  };

  const getGuruColor = (guruId, colorType) => {
    const colors = guruColors[guruId] || guruColors.lynch;
    return colors[colorType] || guruColors.lynch[colorType];
  };

  // 멘토별 보내기 버튼 이미지
  const guruSendButtons = {
    buffett: send2,
    ark: send3,
    lynch: send1,
  };

  const getGuruSendButton = (guruId) => {
    return guruSendButtons[guruId] || send1;
  };

  // 입장 단계 화면 없이 바로 채팅 UI를 렌더링하며, 위 useEffect에서 자동 조인됩니다.

  return (
    <div
      style={{
        width: 402,
        height: 874,
        position: "relative",
        backgroundImage: `url(${personchatback})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundColor: "rgba(217, 217, 217, 0.8)",
        }}
      />

      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column" }}>
        <header style={{ position: "relative", zIndex: 2 }}>
          <div style={{ height: 60, background: "#D9D9D9" }} />
          <div
            style={{
              height: 55,
              background: "white",
              boxShadow: "0px 4px 120px rgba(57, 86, 77, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              paddingInline: 16,
              gap: 16,
            }}
          >
            <img
              src={profile}
              alt="profile"
              style={{ position: "absolute", left: 15, top: 15, width: 25, height: 25 }}
            />
            <div style={{ color: "#27292E", fontSize: 16, fontWeight: 700 }}>
              {room} with {guruLabels[currentGuru] || "피터 린치"}
            </div>
            <div style={{ position: "absolute", right: 15, top: 10, display: "flex", gap: 8 }}>
              <button
                type="button"
                onClick={() =>
                  socket.emit("set_mentor_enabled", {
                    enabled: !mentorEnabled,
                    room,
                  })
                }
                style={{
                  borderRadius: 8,
                  border: "none",
                  background: mentorEnabled ? "#4FA3F7" : "#B0B0B0",
                  color: "#fff",
                  fontSize: 12,
                  padding: "4px 10px",
                  cursor: "pointer",
                }}
              >
                멘토 {mentorEnabled ? "ON" : "OFF"}
              </button>
              {count !== null && (
                <div
                  style={{
                    fontSize: 11,
                    color: "#333",
                    alignSelf: "center",
                  }}
                >
                  로비 {count}명
                </div>
              )}
            </div>
          </div>
        </header>

        <main
          style={{
            flex: 1,
            position: "relative",
            zIndex: 1,
            marginTop: 15,
          }}
        >
          <div
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            style={{
              position: "absolute",
              inset: "0 0 10px 0",
              overflowY: "auto",
              paddingBottom: 120,
              maskImage:
                "linear-gradient(to bottom, rgba(0,0,0,1) 95%, rgba(0,0,0,0) 100%)",
            }}
          >
            {dragOver && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background: "rgba(79,163,247,0.18)",
                  border: "2px dashed rgba(79,163,247,0.6)",
                  borderRadius: 20,
                  zIndex: 2,
                }}
              />
            )}

            <div style={{ position: "relative", zIndex: 1 }}>
              {mentors.map((mentor, index) => (
                <div
                  key={`mentor-${index}`}
                  style={{ display: "flex", flexDirection: "column", marginTop: 10 }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                      paddingLeft: 12,
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: mentor.color,
                        transform: "translateY(3px)",
                      }}
                    />
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: 12,
                        color: "#333",
                        marginTop: 2,
                      }}
                    >
                      {mentor.name}
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                      paddingLeft: 52,
                    }}
                  >
                    <div
                      style={{
                        background: "white",
                        borderRadius: 10,
                        borderTopLeftRadius: 0,
                        padding: "10px 13px",
                        maxWidth: 250,
                        fontSize: 11,
                        lineHeight: "18px",
                        textAlign: "left",
                        boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
                        transform: "translateY(-4px)",
                      }}
                    >
                      {mentor.message}
                      {mentor.message.includes("www.") && (
                        <div
                          style={{
                            width: "100%",
                            height: 100,
                            borderRadius: 8,
                            overflow: "hidden",
                            marginTop: 8,
                            background: "#ccc",
                          }}
                        >
                          <img
                            src="https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg"
                            alt="link-preview"
                            style={{
                              width: "100%",
                              height: "100%",
                              objectFit: "cover",
                            }}
                          />
                        </div>
                      )}
                      {mentor.message.includes("www.") && (
                        <div
                          onClick={() =>
                            openAnalyze({
                              type: "preview",
                              meta: {
                                url: mentor.message,
                                title: mentor.message,
                              },
                            })
                          }
                          style={{
                            marginLeft: 0,
                            marginTop: 10,
                            width: 70,
                            height: 28,
                            background: "#4FA3F7",
                            color: "white",
                            borderRadius: 10,
                            textAlign: "center",
                            lineHeight: "28px",
                            fontSize: 11,
                            fontWeight: "600",
                            cursor: "pointer",
                            boxShadow: "0px 3px 8px rgba(0,0,0,0.15)",
                          }}
                        >
                          분석하기
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {msgs.map((entry, index) => {
                if (entry.type === "system") return renderSystem(entry, index);
                if (entry.type === "preview") return renderPreview(entry, index);
                if (entry.type === "file") return renderFile(entry, index);
                return renderChat(entry, index);
              })}
              <div ref={endRef} />
            </div>
          </div>
        </main>

        <footer
          style={{
            position: "relative",
            zIndex: 2,
            marginTop: "auto",
          }}
        >
          <div
            style={{
              position: "relative",
              width: "100%",
              height: 97,
              background: "white",
              borderTopLeftRadius: 27,
              borderTopRightRadius: 27,
              boxShadow: "0px -4px 120px rgba(57, 86, 77, 0.1)",
            }}
          >
            <div
              style={{
                width: 320,
                height: 36,
                position: "absolute",
                left: "50%",
                transform: "translateX(-50%)",
                bottom: 45,
                background: "#F2F2F2",
                borderRadius: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                paddingLeft: 20,
                paddingRight: 16,
                gap: 10,
              }}
            >
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "none",
                  background: "transparent",
                  fontSize: 18,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 32,
                  height: 32,
                  marginLeft: -12,
                }}
              >
                📎
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                style={{ display: "none" }}
                onChange={(event) =>
                  event.target.files && handleFiles(Array.from(event.target.files))
                }
              />
              <input
                type="text"
                placeholder="입력..."
                value={inputText}
                onChange={(event) => setInputText(event.target.value)}
                onKeyDown={handleKeyDown}
                style={{
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  fontSize: 13,
                  color: "#333",
                  flex: 1,
                  padding: "0 4px",
                }}
              />
              <img
                src={getGuruSendButton(currentGuru)}
                alt="send"
                onClick={() => send(inputText)}
                style={{ width: 18, height: 18, cursor: "pointer" }}
              />
            </div>
          </div>
        </footer>
      </div>

      {(sheetOpen || sheetData) && (
        <>
          <div
            onClick={closeSheet}
            style={{
              position: "absolute",
              inset: 0,
              background: sheetOpen ? "rgba(0,0,0,0.22)" : "transparent",
              opacity: sheetOpen ? 1 : 0,
              transition: "opacity 0.5s ease",
              zIndex: 5,
            }}
          />
          <div
            role="dialog"
            aria-modal="true"
            onPointerDown={onSheetPointerDown}
            style={{
              position: "absolute",
              left: 0,
              bottom: 0,
              width: "100%",
              height: "90vh",
              background: getGuruColor(currentGuru, "popupBackground"),
              borderTopLeftRadius: 25,
              borderTopRightRadius: 25,
              zIndex: 6,
              padding: "16px 24px 0 24px",
              boxSizing: "border-box",
              display: "flex",
              flexDirection: "column",
              transform: sheetDragging
                ? `translateY(${sheetDragY}px)`
                : sheetOpen
                ? "translateY(0%)"
                : "translateY(100%)",
              opacity: sheetOpen ? 1 : 0,
              transition: sheetDragging
                ? "none"
                : sheetOpen
                ? OPEN_TRANSITION
                : CLOSE_TRANSITION,
            }}
          >
            <div
              style={{
                width: 60,
                height: 4,
                borderRadius: 3,
                background: "#ccc",
                margin: "0 auto 12px",
              }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 16, color: "#333" }}>
                {sheetData?.type === "preview" ? "뉴스 분석" : "PDF 분석"}
              </div>
              <button
                type="button"
                onClick={closeSheet}
                style={{
                  border: "none",
                  background: "transparent",
                  fontSize: 14,
                  cursor: "pointer",
                }}
              >
                닫기
              </button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", paddingBottom: 20 }}>
              {/* 뉴스/PDF 내용 박스 */}
              {sheetData?.type === "preview" && sheetData.meta && (
                <div
                  style={{
                    background: "#F5F5F5",
                    borderRadius: 12,
                    padding: 0,
                    marginBottom: 16,
                    overflow: "hidden",
                  }}
                >
                  {sheetData.meta.image && (
                    <div
                      style={{
                        width: "100%",
                        height: 150,
                        overflow: "hidden",
                        background: "#e0e0e0",
                      }}
                    >
                      <img
                        src={sheetData.meta.image}
                        alt={sheetData.meta.title || "뉴스"}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      />
                    </div>
                  )}
                  <div style={{ padding: "8px 20px", textAlign: "center" }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#333", marginBottom: 3 }}>
                      뉴스
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: "#333",
                        marginBottom: 3,
                        lineHeight: "18px",
                      }}
                    >
                      {sheetData.meta.title || sheetData.meta.url}
                    </div>
                    {sheetData.meta.description && (
                      <div
                        style={{
                          fontSize: 10,
                          color: "#666",
                          lineHeight: "11px",
                          textAlign: "left",
                          display: "-webkit-box",
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {sheetData.meta.description}
                      </div>
                    )}
                  </div>
                </div>
              )}
              {sheetData?.type === "file" && sheetData.meta?.file && (
                <div
                  style={{
                    background: "#F5F5F5",
                    borderRadius: 12,
                    padding: "20px",
                    marginBottom: 16,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#333", marginBottom: 8 }}>
                    📄 PDF
                  </div>
                  <div style={{ fontSize: 13, color: "#666" }}>
                    {sheetData.meta.file.name}
                  </div>
                </div>
              )}

              {/* AI 질문 메시지 (상단 고정) */}
              <div style={{ display: "flex", flexDirection: "column", marginBottom: 16 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      overflow: "hidden",
                      transform: "translateY(3px)",
                      background: getGuruColor(currentGuru, "profileBackground"),
                    }}
                  >
                    <img
                      src={getGuruFace(currentGuru)}
                      alt="guru"
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                  </div>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: 12,
                      color: "#333",
                      marginTop: 2,
                    }}
                  >
                    {guruLabels[currentGuru] || "피터 린치"}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                    paddingLeft: 52,
                  }}
                >
                  <div
                    style={{
                      background: "#F9F9F9",
                      borderRadius: 12,
                      borderTopLeftRadius: 0,
                      padding: "10px 14px",
                      maxWidth: "85%",
                      fontSize: 12,
                      lineHeight: "18px",
                      textAlign: "left",
                      boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
                      transform: "translateY(-4px)",
                    }}
                  >
                    {sheetData?.type === "preview"
                      ? "최근 이 뉴스에 대해 어떻게 생각하나? 향후 시장에 어떤 영향을 줄 것 같지?"
                      : "이 PDF 문서의 핵심 내용은 무엇인가? 투자 관점에서 중요한 포인트는?"}
                  </div>
                </div>
              </div>
              {/* 스레드 메시지 렌더 (업로더/AI/기타 사용자 모두 표시) */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
                {sheetThreadMsgs.map((entry, index) => {
                  const msg = entry.msg || {};
                  // 사용자 메시지 판별: role이 "user"이거나 sid가 현재 사용자와 일치
                  // 백엔드에서 보내는 메시지는 sender 필드가 없고 sid, name이 직접 있음
                  const msgSid = msg.sender?.sid || msg.sid;
                  const msgName = msg.sender?.name || msg.name;
                  const isMe = msg.role === "user" || msgSid === (socket.id || myId);
                  const cleaned = (msg.text || "").replace(/\[thread:(file|url):[^\]]+\]\s*$/i, "").replace(/\[thread:[^\]]+\]/i, "");
                  
                  // AI 여부 판별 및 표시 이름 결정
                  const isAI = msg.role === "assistant" || msgSid === "ai" || (!msgSid && msg.role !== "user");
                  const displayName = isAI 
                    ? (guruLabels[currentGuru] || "피터 린치")
                    : (msgName || "사용자");
                  
                  if (isMe) {
                    // 사용자 메시지: 우측에 프로필과 이름 표시
                    return (
                      <div key={`sheetme-${index}`} style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", paddingRight: 6 }}>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, flexDirection: "row-reverse" }}>
                          <div
                            style={{
                              width: 28,
                              height: 28,
                              borderRadius: "50%",
                              overflow: "hidden",
                              background: "#5353b0ff",
                            }}
                          >
                            <img 
                              src={profile} 
                              alt="user" 
                              style={{ width: "100%", height: "100%", objectFit: "cover" }} 
                            />
                          </div>
                          <div style={{ fontWeight: 700, fontSize: 12, color: "#333", marginTop: 2 }}>
                            {msgName || displayName || "나"}
                          </div>
                        </div>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, paddingRight: 36, marginTop: -4 }}>
                          <div
                            style={{
                              background: "#fbeb56ff",
                              borderRadius: 12,
                              borderTopRightRadius: 0,
                              padding: "10px 14px",
                              maxWidth: 280,
                              fontSize: 12,
                              lineHeight: "18px",
                              boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
                            }}
                          >
                            {cleaned}
                          </div>
                        </div>
                      </div>
                    );
                  }
                  // 상대/AI
                  
                  return (
                    <div key={`sheetother-${index}`} style={{ display: "flex", flexDirection: "column" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                        <div
                          style={{
                            width: 28,
                            height: 28,
                            borderRadius: "50%",
                            overflow: "hidden",
                            background: isAI ? getGuruColor(currentGuru, "profileBackground") : "#5353b0ff",
                          }}
                        >
                          <img 
                            src={isAI ? getGuruFace(currentGuru) : profile} 
                            alt={isAI ? "guru" : "user"} 
                            style={{ width: "100%", height: "100%", objectFit: "cover" }} 
                          />
                        </div>
                        <div style={{ fontWeight: 700, fontSize: 12, color: "#333", marginTop: 2 }}>
                          {displayName}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, paddingLeft: 36 }}>
                        <div
                          style={{
                            background: "#F9F9F9",
                            borderRadius: 12,
                            borderTopLeftRadius: 0,
                            padding: "10px 14px",
                            maxWidth: 280,
                            fontSize: 12,
                            lineHeight: "18px",
                            boxShadow: "0px 2px 6px rgba(0,0,0,0.08)",
                          }}
                        >
                          {cleaned}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 답변 입력 필드 (업로더만 표시) */}
            {Boolean(sheetData?.meta?.ownerSid && (sheetData.meta.ownerSid === (socket.id || myId))) && (
              <div
                style={{
                  position: "sticky",
                  bottom: 0,
                  background: "#fff",
                  padding: "12px 24px",
                  borderTop: "1px solid #E0E0E0",
                  display: "flex",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    width: 320,
                    height: 36,
                    background: "#F2F2F2",
                    borderRadius: 32,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    paddingLeft: 20,
                    paddingRight: 16,
                    gap: 10,
                  }}
                >
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      border: "none",
                      background: "transparent",
                      fontSize: 18,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 32,
                      height: 32,
                      marginLeft: -12,
                    }}
                  >
                    📎
                  </button>
                  <input
                    type="text"
                    placeholder="입력..."
                    value={sheetAnswer}
                    onChange={(e) => setSheetAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (sheetAnswer.trim()) {
                          sendSheetMessage();
                        }
                      }
                    }}
                    style={{
                      border: "none",
                      outline: "none",
                      background: "transparent",
                      fontSize: 13,
                      color: "#333",
                      flex: 1,
                      padding: "0 4px",
                    }}
                  />
                  <img
                    src={getGuruSendButton(currentGuru)}
                    alt="send"
                    onClick={() => {
                      if (sheetAnswer.trim()) {
                        sendSheetMessage();
                      }
                    }}
                    style={{ width: 18, height: 18, cursor: "pointer" }}
                  />
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
