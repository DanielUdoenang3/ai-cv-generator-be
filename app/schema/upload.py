from pydantic import BaseModel, Field
from typing import Optional, List

class FileUploadResponse(BaseModel):
    url: str = Field(..., description="Secure CDN URL of the uploaded file on Cloudinary")
    public_id: str = Field(..., description="Cloudinary unique public ID of the resource")
    original_filename: str = Field(..., description="Original filename submitted by user")
    resource_type: str = Field(..., description="Cloudinary resource type (image, raw, video)")
    format: Optional[str] = Field(None, description="File extension / format")
    bytes: int = Field(..., description="Size of file in bytes")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://res.cloudinary.com/demo/image/upload/v1600000000/ai_cv_generator/resumes/my_resume.pdf",
                "public_id": "ai_cv_generator/resumes/my_resume",
                "original_filename": "my_resume.pdf",
                "resource_type": "raw",
                "format": "pdf",
                "bytes": 245000
            }
        }


class MultipleFileUploadResponse(BaseModel):
    total: int = Field(..., description="Total number of uploaded files")
    files: List[FileUploadResponse] = Field(..., description="List of uploaded file metadata objects")
