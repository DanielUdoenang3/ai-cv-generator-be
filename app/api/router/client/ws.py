"""
Public Client WebSocket endpoint.

Connection URL:
    ws://<host>/api/v1/public/submissions/{submission_id}/ws?token={access_token}

Auth: the access_token query param is validated against the Submission row.
      Invalid token → connection closed with code 4001.

Client → Server messages (JSON text frames):
    {"type": "ping"}                          → server replies {"type": "pong"}
    {"type": "typing", "is_typing": true}     → broadcast typing event to room

Server → Client events:
    See websocket_manager.py broadcast payloads — event types:
    new_message | message_updated | message_deleted | read_receipt |
    typing | submission_status_changed | submission_assigned
"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.submissions import Submission
from app.utils.websocket_manager import manager

client_ws_router = APIRouter(tags=["Public Client WebSocket"])


@client_ws_router.websocket("/public/submissions/{submission_id}/ws")
async def client_ws_endpoint(
    websocket: WebSocket,
    submission_id: str,
    token: str = Query(..., description="Client access token (from submission creation response)"),
    db: Session = Depends(get_db),
):
    try:
        submission = db.query(Submission).filter(
            Submission.id == submission_id,
            Submission.access_token == token,
        ).first()

        if not submission:
            await websocket.close(code=4001)
            return

        # Eagerly load the client name before closing the DB session
        client_name = submission.client.first_name if submission.client else "Client"

    finally:
        db.close()

    await manager.connect(submission_id, websocket)
    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "typing":
                is_typing = bool(data.get("is_typing", False))
                await manager.broadcast_to_submission(submission_id, {
                    "event": "typing",
                    "data": {
                        "sender_type": "client",
                        "sender_name": client_name,
                        "is_typing": is_typing,
                    },
                })

    finally:
        manager.disconnect(submission_id, websocket)
