from fastapi import APIRouter
from app.api.controller.client.upload import upload_file_controller

upload_router = APIRouter(prefix="/upload", tags=["File Uploads"])

upload_router.add_api_route(
    "",
    endpoint=upload_file_controller,
    methods=["POST"],
    summary="Upload Document / Media File",
    description=(
        "Uploads a document (.pdf, .docx, .doc), image (.png, .jpg), video (.mp4), "
        "or chat attachment to Cloudinary and returns CDN secure_url and metadata."
    ),
)
