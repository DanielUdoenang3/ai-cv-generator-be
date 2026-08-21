from typing import Optional, List
from fastapi import UploadFile, File, Form, status
from app.utils.cloudinary import upload_file_to_cloudinary, upload_multiple_files_to_cloudinary
from app.utils.custom_response import success_response, error_response


async def upload_file_controller(
    files: List[UploadFile] = File(...),
    folder: Optional[str] = Form("ai_cv_generator/uploads"),
):
    """
    Uploads single or multiple files to Cloudinary for resumes, images, videos, and chat attachments.
    """
    if not files:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No file provided. Please attach at least one file.",
        )

    folder_name = folder or "ai_cv_generator/uploads"

    if len(files) == 1:
        result = await upload_file_to_cloudinary(file=files[0], folder=folder_name)
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="File uploaded successfully to Cloudinary",
            data=result,
        )
    else:
        results = await upload_multiple_files_to_cloudinary(files=files, folder=folder_name)
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{len(results)} files uploaded successfully to Cloudinary",
            data={
                "total": len(results),
                "files": results,
            },
        )
