from abc import ABC, abstractmethod
from fastapi import WebSocket


class BasePubSubBackend(ABC):
    """
    Abstract contract for WebSocket pub/sub backends.

    Concrete implementations:
      - InMemoryBackend  — single-process, zero deps (WS_BACKEND=memory)
      - RedisPubSubBackend — multi-worker safe via Redis channels (WS_BACKEND=redis)

    Consumers call manager.broadcast_to_submission() and never touch the backend directly.
    """

    @abstractmethod
    async def connect(self, submission_id: str, websocket: WebSocket) -> None:
        """Accept the WebSocket and register it under submission_id."""
        ...

    @abstractmethod
    def disconnect(self, submission_id: str, websocket: WebSocket) -> None:
        """Remove the WebSocket from the submission_id room."""
        ...

    @abstractmethod
    async def broadcast_to_submission(self, submission_id: str, payload: dict) -> None:
        """Push a JSON payload to every active connection in the room."""
        ...
