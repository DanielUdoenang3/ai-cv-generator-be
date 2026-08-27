from fastapi import APIRouter
from app.api.controller.admin.document import (
    render_cv_documents_controller,
    list_documents_controller,
    download_document_controller,
)

admin_document_router = APIRouter(tags=["Admin CV Documents"])

admin_document_router.add_api_route(
    "/submissions/{submission_id}/documents/render",
    render_cv_documents_controller,
    methods=["POST"],
    summary="Render CV documents (PDF/DOCX) for a submission — Admin Triggered (Admin only)",
)

admin_document_router.add_api_route(
    "/submissions/{submission_id}/documents",
    list_documents_controller,
    methods=["GET"],
    summary="List all generated documents for a submission (Admin only)",
)

admin_document_router.add_api_route(
    "/submissions/{submission_id}/documents/{document_id}/download",
    download_document_controller,
    methods=["GET"],
    summary="Download a generated CV document as a binary file (Admin only)",
)
