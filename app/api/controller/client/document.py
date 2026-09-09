import httpx
from fastapi import Depends, Header, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.submissions import Submission
from app.models.chats import Conversation, Message
from app.services.document_service import (
    download_document_service,
    list_client_documents_service,
    proxy_attachment_service,
    _ATTACHMENT_MIME,
)

_MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def client_list_documents_controller(
    submission_id: str,
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    db: Session = Depends(get_db),
):
    return await list_client_documents_service(
        submission_id=submission_id,
        access_token=x_client_access_token,
        db=db,
    )


async def _get_client_submission(
    submission_id: str,
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    db: Session = Depends(get_db),
) -> Submission:
    """Validate the client's access token and return their submission."""
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.access_token == x_client_access_token,
    ).first()
    return submission


async def client_download_document_controller(
    submission_id: str,
    document_id: str,
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    db: Session = Depends(get_db),
):
    # Validate client owns this submission
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.access_token == x_client_access_token,
    ).first()

    if not submission:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Invalid access token or submission not found"},
        )

    doc, result = await download_document_service(submission_id, document_id, db)
    if doc is None:
        return result  # error_response JSON

    file_ext = (doc.file_type or "pdf").lower()
    content_type = _MIME_TYPES.get(file_ext, "application/octet-stream")
    filename = f"{doc.document_kind or 'document'}.{file_ext}"

    async def _stream():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", result) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    yield chunk

    return StreamingResponse(
        _stream(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


async def client_proxy_attachment_controller(
    submission_id: str,
    public_id: str = Query(..., description="Cloudinary public_id of the chat attachment"),
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    db: Session = Depends(get_db),
):
    """
    Stream a Cloudinary chat attachment for a client.

    Validates that the public_id appears in the conversation for the caller's
    submission (so clients can only access their own attachments), then fetches
    the asset server-side via the Admin API and streams it inline.
    """
    # 1. Verify the access token
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.access_token == x_client_access_token,
    ).first()
    if not submission:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Invalid access token or submission not found"},
        )

    # 2. Confirm the public_id belongs to this submission's conversation
    #    (prevents a client using a valid token to fetch another client's files)
    conv = db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()

    attachment_found = False
    if conv:
        messages = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).all()
        for msg in messages:
            for att in (msg.attachments or []):
                if isinstance(att, dict) and att.get("public_id") == public_id:
                    attachment_found = True
                    break
            if attachment_found:
                break

    if not attachment_found:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Attachment not found in this submission"},
        )

    # 3. Proxy the file
    try:
        download_url, ext = await proxy_attachment_service(public_id)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(exc)},
        )

    content_type = _ATTACHMENT_MIME.get(ext, "application/octet-stream")
    filename = public_id.split("/")[-1]

    async def _stream():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", download_url) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    yield chunk

    return StreamingResponse(
        _stream(),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
