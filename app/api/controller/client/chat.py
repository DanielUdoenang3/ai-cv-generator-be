from typing import Optional, List
from fastapi import Depends, Header, Form, File, UploadFile
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.services.client.chat import get_messages, send_message

async def get_messages_controller(
    submission_id: str,
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    db: Session = Depends(get_db),
):
    return await get_messages(
        submission_id=submission_id,
        access_token=x_client_access_token,
        db=db,
    )

async def send_message_controller(
    submission_id: str,
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    message: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    """
    Clean client chat message endpoint.
    Accepts text message and/or direct file attachments (uploaded automatically to Cloudinary).
    """
    return await send_message(
        submission_id=submission_id,
        access_token=x_client_access_token,
        db=db,
        message_text=message,
        raw_files=files,
    )
