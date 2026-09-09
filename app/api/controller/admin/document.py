import httpx
from fastapi import Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.services import get_current_admin
from app.schema.ai import DocumentRenderRequest
from app.services.document_service import (
    render_cv_documents_service,
    list_submission_documents_service,
    download_document_service,
    proxy_attachment_service,
    _ATTACHMENT_MIME,
)

_MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def render_cv_documents_controller(
    submission_id: str,
    payload: DocumentRenderRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await render_cv_documents_service(submission_id, payload, current_admin, db)


async def list_documents_controller(
    submission_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await list_submission_documents_service(submission_id, current_admin, db)


async def download_document_controller(
    submission_id: str,
    document_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    doc, result = await download_document_service(submission_id, document_id, db)
    if doc is None:
        return result  # error_response

    # Fetch the file from Cloudinary's Admin API and stream it directly to the
    # client.  We do NOT redirect: the CDN delivery URL returns 401 on the free
    # plan for raw assets; the private_download_url we now generate requires the
    # Cloudinary API key in the query string, which we don't want to expose to
    # the browser.
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


async def proxy_attachment_controller(
    public_id: str = Query(..., description="Cloudinary public_id of the chat attachment"),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Stream a Cloudinary chat attachment through the backend.

    The browser cannot open Cloudinary raw/image CDN URLs directly on the free
    plan (401). This endpoint fetches the asset server-side via the Admin API
    (private_download_url) and streams the bytes back, so the client never
    needs to hit Cloudinary directly.
    """
    try:
        download_url, ext = await proxy_attachment_service(public_id)
    except ValueError as exc:
        from app.utils.custom_response import error_response
        from fastapi import status as http_status
        return error_response(status_code=http_status.HTTP_400_BAD_REQUEST, message=str(exc))

    content_type = _ATTACHMENT_MIME.get(ext, "application/octet-stream")
    filename = public_id.split("/")[-1]  # last segment, e.g. "stream_ycjjqv.pdf"

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
