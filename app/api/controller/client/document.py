import httpx
from fastapi import Depends, Header, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.submissions import Submission
from app.services.document_service import download_document_service, list_client_documents_service

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
