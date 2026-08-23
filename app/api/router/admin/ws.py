"""
Admin/Staff WebSocket endpoint.

Connection URL:
    ws://<host>/api/v1/admin/submissions/{submission_id}/ws?token={jwt_token}

Auth: the JWT token query param is decoded and validated against the admins table.
      Invalid/expired token → connection closed with code 4001.

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
from app.models.admins import Admin
from app.utils.token import decode_access_token
from app.utils.websocket_manager import manager

admin_ws_router = APIRouter(tags=["Admin WebSocket"])


@admin_ws_router.websocket("/submissions/{submission_id}/ws")
async def admin_ws_endpoint(
    websocket: WebSocket,
    submission_id: str,
    token: str = Query(..., description="Admin JWT access token"),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(token)
        if not payload:
            await websocket.close(code=4001)
            return

        email = payload.get("email")
        if not email:
            await websocket.close(code=4001)
            return

        admin = db.query(Admin).filter(
            Admin.email == email,
            Admin.is_active == True,
        ).first()

        if not admin:
            await websocket.close(code=4001)
            return

        admin_name = f"{admin.first_name} {admin.last_name}"

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
                        "sender_type": "staff",
                        "sender_name": admin_name,
                        "is_typing": is_typing,
                    },
                })

    finally:
        manager.disconnect(submission_id, websocket)
