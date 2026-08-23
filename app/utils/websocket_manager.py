"""
WebSocket Connection Manager — the single import point for all broadcast calls.

Usage everywhere in the codebase:
    from app.utils.websocket_manager import manager

    await manager.broadcast_to_submission(submission_id, payload)

The backend is chosen at startup via the WS_BACKEND environment variable:
    WS_BACKEND=memory   (default) — InMemoryBackend, single-worker
    WS_BACKEND=redis    (future)  — RedisPubSubBackend, multi-worker Hetzner

To migrate to Redis on Hetzner:
    1. pip install "redis[asyncio]"
    2. Set WS_BACKEND=redis and REDIS_URL=redis://... in .env
    3. Restart — zero code changes required.
"""

from app.utils.ws_backends.base import BasePubSubBackend


def _create_backend() -> BasePubSubBackend:
    from app.utils.settings import settings

    backend = settings.WS_BACKEND.strip().lower()

    if backend == "redis":
        from app.utils.ws_backends.redis_backend import RedisPubSubBackend
        return RedisPubSubBackend()

    # Default: memory
    from app.utils.ws_backends.memory import InMemoryBackend
    return InMemoryBackend()


manager: BasePubSubBackend = _create_backend()
