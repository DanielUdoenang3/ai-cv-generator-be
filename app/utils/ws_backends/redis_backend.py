"""
Redis Pub/Sub backend — for multi-worker deployments (Hetzner, VPS with uvicorn --workers N).

Activation:
    1. pip install "redis[asyncio]"  (already in requirements.txt — uncomment it)
    2. Set .env:  WS_BACKEND=redis
                  REDIS_URL=redis://:password@your-host:6379/0

How it works:
    - Each WebSocket connection subscribes to channel: ws:submission:{submission_id}
    - broadcast_to_submission() publishes the payload to that Redis channel
    - A per-worker background listener task reads from all subscribed channels
      and forwards messages to local WebSocket connections
    - Worker A and Worker B each forward to their own local sockets,
      so all sockets across all workers receive the event
"""

import asyncio
import json

from fastapi import WebSocket

from app.utils.ws_backends.base import BasePubSubBackend


class RedisPubSubBackend(BasePubSubBackend):
    def __init__(self):
        # Local socket registry (per-worker)
        self._connections: dict[str, list[WebSocket]] = {}
        self._redis = None
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None

    # ------------------------------------------------------------------ helpers

    def _channel(self, submission_id: str) -> str:
        return f"ws:submission:{submission_id}"

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
            except ImportError:
                raise RuntimeError(
                    "WS_BACKEND=redis requires the redis package. "
                    "Run: pip install 'redis[asyncio]'"
                )
            from app.utils.settings import settings
            self._redis = await aioredis.from_url(
                settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
            )
        return self._redis

    async def _get_pubsub(self):
        if self._pubsub is None:
            redis = await self._get_redis()
            self._pubsub = redis.pubsub()
        return self._pubsub

    # ------------------------------------------------------------------ interface

    async def connect(self, submission_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(submission_id, []).append(websocket)

        pubsub = await self._get_pubsub()
        await pubsub.subscribe(self._channel(submission_id))

        # Start the background listener once
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen())

    def disconnect(self, submission_id: str, websocket: WebSocket) -> None:
        room = self._connections.get(submission_id, [])
        if websocket in room:
            room.remove(websocket)

    async def broadcast_to_submission(self, submission_id: str, payload: dict) -> None:
        """Publish to Redis channel — all workers' listeners will forward to their local sockets."""
        redis = await self._get_redis()
        await redis.publish(self._channel(submission_id), json.dumps(payload))

    # ------------------------------------------------------------------ listener

    async def _listen(self):
        """Background task: relay Redis pub/sub messages to local WebSocket connections."""
        pubsub = await self._get_pubsub()
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue

                channel: str = message["channel"]          # "ws:submission:{id}"
                submission_id = channel.removeprefix("ws:submission:")
                payload = json.loads(message["data"])

                stale: list[WebSocket] = []
                for ws in list(self._connections.get(submission_id, [])):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        stale.append(ws)

                for ws in stale:
                    self.disconnect(submission_id, ws)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            # Log and allow the task to die; next connect() will restart it
            print(f"[RedisPubSubBackend] listener error: {exc}")
