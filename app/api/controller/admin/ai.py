from fastapi import Depends
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.services import get_current_admin
from app.schema.ai import CvGenerateRequest
from app.services.ai_service import (
    generate_cv_service,
    get_submission_generations_service,
    get_ai_models_service,
)


async def generate_cv_controller(
    submission_id: str,
    payload: CvGenerateRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await generate_cv_service(submission_id, payload, current_admin, db)


async def get_submission_generations_controller(
    submission_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await get_submission_generations_service(submission_id, current_admin, db)


async def get_ai_models_controller(
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Returns the list of available OpenAI chat models for the frontend
    model-selection dropdown on the Tailor Resume page.
    Falls back to a curated hardcoded list if the OpenAI API is unreachable.
    """
    return await get_ai_models_service(current_admin)
