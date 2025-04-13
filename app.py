import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from google.genai.types import Part, Content
from google.adk.runners import Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from google.genai import types
from spritle_agent.agent import root_agent

load_dotenv()

APP_NAME = "ADK Streaming example"
session_service = InMemorySessionService()

def start_agent_session(session_id: str):
    session = session_service.create_session(app_name=APP_NAME, user_id=session_id, session_id=session_id)
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)
    run_config = RunConfig(response_modalities=["AUDIO"],speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
        )
    ))
    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(session=session, live_request_queue=live_request_queue, run_config=run_config)
    return live_events, live_request_queue

app = FastAPI()
STATIC_DIR = Path("static")
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    """Serves the index.html"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

live_events, live_request_queue = start_agent_session("#729092158")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async def send_agent_events():
        async for event in live_events:
            

            part = event.content and event.content.parts and event.content.parts[0]
            print(part)

            if part and part.inline_data and hasattr(part.inline_data, "data"):
                await websocket.send_bytes(part.inline_data.data)
            
            
    agent_task = asyncio.create_task(send_agent_events())

    while True:
            audio_bytes = await websocket.receive_bytes()
            content = Content(role="user", parts=[Part.from_bytes(data=audio_bytes, mime_type="audio/webm")])
            live_request_queue.send_content(content=content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
