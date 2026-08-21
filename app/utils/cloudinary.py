import os
import logging
from typing import Dict, Any, Optional, List
from fastapi import UploadFile, HTTPException, status
import cloudinary
import cloudinary.uploader
from app.utils.settings import settings

from app.utils.custom_response import error_response

logger = logging.getLogger(__name__)

# Configure Cloudinary SDK
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# Allowed file extensions & size limits
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".rtf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a"}

ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

MAX_DOCUMENT_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_MEDIA_SIZE = 25 * 1024 * 1024          # 25 MB


def validate_file(file: UploadFile) -> str:
    """
    Validates file extension and size.
    Returns the file category: 'document', 'image', 'video', or 'audio'.
    """
    filename = file.filename or "unknown"
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Determine size limit based on extension category
    if ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS:
        max_size = MAX_MEDIA_SIZE
        category = "video" if ext in VIDEO_EXTENSIONS else "audio"
    elif ext in IMAGE_EXTENSIONS:
        max_size = MAX_DOCUMENT_IMAGE_SIZE
        category = "image"
    else:
        max_size = MAX_DOCUMENT_IMAGE_SIZE
        category = "document"

    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"File size exceeds maximum allowed limit of {max_size_mb:.0f}MB",
        )

    return category


async def upload_file_to_cloudinary(
    file: UploadFile,
    folder: str = "ai_cv_generator/general",
) -> Dict[str, Any]:
    """
    Uploads a single FastAPI UploadFile to Cloudinary.
    Returns structured dict with secure_url, public_id, resource_type, bytes, etc.
    """
    category = validate_file(file)
    original_filename = file.filename or "uploaded_file"

    try:
        resource_type = "auto"
        if category == "document" and not original_filename.lower().endswith(".pdf"):
            resource_type = "raw"

        response = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True,
        )

        return {
            "url": response.get("secure_url"),
            "public_id": response.get("public_id"),
            "original_filename": original_filename,
            "resource_type": response.get("resource_type"),
            "format": response.get("format") or os.path.splitext(original_filename)[1].lstrip("."),
            "bytes": response.get("bytes", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {str(e)}")
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to upload file to Cloudinary: {str(e)}",
        )


async def upload_multiple_files_to_cloudinary(
    files: List[UploadFile],
    folder: str = "ai_cv_generator/general",
) -> List[Dict[str, Any]]:
    """
    Uploads multiple FastAPI UploadFiles to Cloudinary.
    Returns a list of structured file metadata dicts.
    """
    if not files:
        return []

    if len(files) > 10:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Maximum of 10 files can be uploaded per batch request.",
        )

    results = []
    for file in files:
        result = await upload_file_to_cloudinary(file, folder=folder)
        results.append(result)

    return results
