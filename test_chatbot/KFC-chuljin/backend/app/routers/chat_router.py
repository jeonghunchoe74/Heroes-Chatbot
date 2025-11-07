from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatMessage, ChatResponse
from app.sockets.chat_server import ChatServer

router = APIRouter()
chat_server = ChatServer()


@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """
    단톡방 메시지 전송 (Socket.io 연결)
    """
    try:
        response = await chat_server.handle_message(message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rooms")
async def get_chat_rooms():
    """
    활성 채팅방 목록 조회
    """
    try:
        rooms = await chat_server.get_active_rooms()
        return {"rooms": rooms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

