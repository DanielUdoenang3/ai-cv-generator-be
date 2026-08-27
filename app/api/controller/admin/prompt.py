from fastapi import Depends
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.services import get_current_admin
from app.schema.ai import PromptCreate, PromptUpdate
from app.services.admin.prompt import (
    list_prompts_service,
    create_prompt_service,
    update_prompt_service,
    activate_prompt_service,
    deactivate_prompt_service,
    duplicate_prompt_service,
    delete_prompt_service,
)


async def list_prompts_controller(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await list_prompts_service(current_admin, db)


async def create_prompt_controller(
    payload: PromptCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await create_prompt_service(payload, current_admin, db)


async def update_prompt_controller(
    prompt_id: str,
    payload: PromptUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await update_prompt_service(prompt_id, payload, current_admin, db)


async def activate_prompt_controller(
    prompt_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await activate_prompt_service(prompt_id, current_admin, db)


async def deactivate_prompt_controller(
    prompt_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await deactivate_prompt_service(prompt_id, current_admin, db)


async def duplicate_prompt_controller(
    prompt_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await duplicate_prompt_service(prompt_id, current_admin, db)


async def delete_prompt_controller(
    prompt_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await delete_prompt_service(prompt_id, current_admin, db)

