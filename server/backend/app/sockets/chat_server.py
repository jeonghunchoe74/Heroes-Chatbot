import socketio
from app.services.guru_service import get_guru_prompt
from app.core.openai_client import ask_gpt

sio = socketio.AsyncServer(cors_allowed_origins="*")
sio_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"✅ User connected: {sid}")

@sio.event
async def chat_message(sid, data):
    guru = data.get("guru", "buffett")
    prompt = get_guru_prompt(guru)
    msg = data.get("message", "")

    reply = await ask_gpt([
        {"role": "system", "content": prompt},
        {"role": "user", "content": msg}
    ])
    await sio.emit("chat_message", {"user": guru, "text": reply})

@sio.event
async def disconnect(sid):
    print(f"❌ User disconnected: {sid}")
