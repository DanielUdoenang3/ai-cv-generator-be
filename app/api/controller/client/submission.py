from fastapi import Depends, Header
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.schema.submission import CreateSubmission
from app.services.client.submission import create_submission, get_submission_status

async def create_submission_controller(
    data: CreateSubmission,
    db: Session = Depends(get_db),
):
    return await create_submission(data=data, db=db)

async def get_submission_status_controller(
    submission_id: str,
    x_client_access_token: str = Header(..., alias="X-Client-Access-Token"),
    db: Session = Depends(get_db),
):
    return await get_submission_status(
        submission_id=submission_id,
        access_token=x_client_access_token,
        db=db,
    )
