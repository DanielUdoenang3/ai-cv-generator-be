from fastapi import Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.services import get_current_admin
from app.schema.ai import DocumentRenderRequest
from app.services.document_service import (
    render_cv_documents_service,
    list_submission_documents_service,
    download_document_service,
)


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

    # result is now a signed URL — redirect the client directly to Cloudinary
    return RedirectResponse(url=result, status_code=302)
