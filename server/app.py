import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from server.ws import WebSocketManager
from server.routes import router, init_routes

logger = logging.getLogger(__name__)

def create_app(agents, kis_client, config) -> tuple[FastAPI, WebSocketManager]:
    app = FastAPI(title="Agent Trading Company", version="1.0.0")

    # CORS for React frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize routes with dependencies
    init_routes(agents, kis_client, config)
    app.include_router(router)

    # WebSocket manager
    ws_manager = WebSocketManager()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle client messages if needed
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    return app, ws_manager
