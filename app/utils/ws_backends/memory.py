from fastapi import WebSocket

from app.utils.ws_backends.base import BasePubSubBackend


class InMemoryBackend(BasePubSubBackend):
    """
    In-process WebSocket connection registry.
    Perfect for single-worker deployments (Railway, Render free tier, etc.).

    Switch to RedisPubSubBackend when running uvicorn --workers N > 1.
    Set WS_BACKEND=memory in .env (this is the default).
    """

    def __init__(self):
        # submission_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, submission_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(submission_id, []).append(websocket)

    def disconnect(self, submission_id: str, websocket: WebSocket) -> None:
        room = self._connections.get(submission_id, [])
        if websocket in room:
            room.remove(websocket)

    async def broadcast_to_submission(self, submission_id: str, payload: dict) -> None:
        """
        Send payload to every socket in the room.
        Stale/closed sockets are silently pruned.
        """
        stale: list[WebSocket] = []

        for ws in list(self._connections.get(submission_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)

        for ws in stale:
            self.disconnect(submission_id, ws)
