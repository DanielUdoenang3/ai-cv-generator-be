from fastapi import APIRouter
from app.api.controller.client.document import (
    client_download_document_controller,
    client_list_documents_controller,
    client_proxy_attachment_controller,
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

client_document_router.add_api_route(
    "/submissions/{submission_id}/attachments/proxy",
    client_proxy_attachment_controller,
    methods=["GET"],
    summary="Proxy a Cloudinary chat attachment (Client access token required)",
    description=(
        "Pass the Cloudinary public_id as a query param. "
        "The backend validates the attachment belongs to the caller's submission, "
        "then fetches and streams the file inline — no direct Cloudinary CDN access needed."
    ),
)

