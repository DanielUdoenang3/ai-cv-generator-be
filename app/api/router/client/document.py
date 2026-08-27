from fastapi import APIRouter
from app.api.controller.client.document import (
    client_download_document_controller,
    client_list_documents_controller,
)

client_document_router = APIRouter(prefix="/public", tags=["Client CV Documents"])

client_document_router.add_api_route(
    "/submissions/{submission_id}/documents",
    client_list_documents_controller,
    methods=["GET"],
    summary="List all generated CV documents for your request (Client access token required)",
)

client_document_router.add_api_route(
    "/submissions/{submission_id}/documents/{document_id}/download",
    client_download_document_controller,
    methods=["GET"],
    summary="Download your CV document as a binary file (Client access token required)",
)

