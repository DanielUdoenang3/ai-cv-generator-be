from typing import Optional, List
from fastapi import status
from sqlalchemy.orm import Session

from app.models.prompts import Prompt
from app.models.admins import Admin
from app.models.enums import AdminRole
from app.schema.ai import PromptCreate, PromptUpdate
from app.utils.custom_response import success_response, error_response

# Default fallback system prompt templates matching UI
DEFAULT_PROMPT_TEMPLATES = [
    {
        "name": "Software Engineer CV",
        "description": "Optimized prompt for software engineering roles",
        "category": "Technology",
        "content": "Create a professional CV for a {role} position at {company}. Highlight technical skills, project experience, and achievements. Focus on {keywords}.",
        "usage_count": 156,
        "is_active": True,
    },
    {
        "name": "Product Manager CV",
        "description": "Prompt for product management positions",
        "category": "Product",
        "content": "Develop a CV for {role} at {company}. Emphasize leadership, product launches, cross-functional collaboration, and metrics. Include {keywords}.",
        "usage_count": 89,
        "is_active": True,
    },
    {
        "name": "Executive CV",
        "description": "High-level executive resume template",
        "category": "Executive",
        "content": "Craft an executive CV for {role} at {company}. Focus on strategic vision, team building, revenue growth, and board experience. Keywords: {keywords}.",
        "usage_count": 45,
        "is_active": True,
    },
    {
        "name": "Marketing Professional CV",
        "description": "Template for marketing roles",
        "category": "Marketing",
        "content": "Generate a CV for {role} position at {company}. Highlight campaigns, ROI, brand strategy, and digital marketing skills. Include {keywords}.",
        "usage_count": 67,
        "is_active": False,
    },
]


def seed_default_prompts_if_empty(db: Session) -> List[Prompt]:
    """Helper method — seeds default role-specific prompts if the table is empty."""
    existing_count = db.query(Prompt).count()
    if existing_count == 0:
        created_prompts = []
        for p_data in DEFAULT_PROMPT_TEMPLATES:
            prompt = Prompt(
                name=p_data["name"],
                description=p_data["description"],
                category=p_data["category"],
                content=p_data["content"],
                version=1,
                is_active=p_data["is_active"],
                usage_count=p_data["usage_count"],
                created_by_id=None,
            )
            db.add(prompt)
            created_prompts.append(prompt)
        db.commit()
        for p in created_prompts:
            db.refresh(p)
        return created_prompts
    return db.query(Prompt).all()


def get_active_master_prompt(db: Session) -> Prompt:
    """Helper method — retrieves active system prompt or seeds default prompts if none exist."""
    prompts = db.query(Prompt).filter(Prompt.is_active == True).order_by(Prompt.updated_at.desc()).all()
    if prompts:
        return prompts[0]
    
    # If no active prompt exists, seed initial prompts
    seeded = seed_default_prompts_if_empty(db)
    active_seeded = [p for p in seeded if p.is_active]
    if active_seeded:
        return active_seeded[0]
    
    # Fallback to latest
    any_prompt = db.query(Prompt).order_by(Prompt.created_at.desc()).first()
    if any_prompt:
        any_prompt.is_active = True
        db.commit()
        db.refresh(any_prompt)
        return any_prompt
    
    # Fallback safety
    fallback = Prompt(
        name="Default Master CV Prompt",
        description="Fallback system prompt",
        category="General",
        content=DEFAULT_PROMPT_TEMPLATES[0]["content"],
        version=1,
        is_active=True,
    )
    db.add(fallback)
    db.commit()
    db.refresh(fallback)
    return fallback


async def list_prompts_service(current_admin: Admin, db: Session):
    """
    Returns all system prompt templates and summary stats.
    Restricted to Super Admin role to protect master AI instructions.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can access system prompt templates",
        )

    # Ensure default prompts are seeded if table is empty
    seed_default_prompts_if_empty(db)

    prompts = db.query(Prompt).order_by(Prompt.created_at.desc()).all()

    total_prompts = len(prompts)
    active_prompts = sum(1 for p in prompts if p.is_active)
    total_usage = sum(p.usage_count or 0 for p in prompts)

    prompt_list = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "content": p.content,
            "version": p.version,
            "is_active": p.is_active,
            "usage_count": p.usage_count,
            "created_by_id": p.created_by_id,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in prompts
    ]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Prompts retrieved successfully",
        data={
            "stats": {
                "total_prompts": total_prompts,
                "active_prompts": active_prompts,
                "total_usage": total_usage,
            },
            "prompts": prompt_list,
        },
    )


async def create_prompt_service(payload: PromptCreate, current_admin: Admin, db: Session):
    """
    Creates a new system prompt template or version.
    Restricted to Super Admin role.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can create system prompts",
        )

    existing_count = db.query(Prompt).filter(Prompt.name == payload.name).count()
    version = existing_count + 1

    prompt = Prompt(
        name=payload.name,
        description=payload.description,
        category=payload.category or "General",
        content=payload.content,
        version=version,
        is_active=payload.is_active,
        usage_count=0,
        created_by_id=current_admin.id,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="System prompt created successfully",
        data={
            "id": prompt.id,
            "name": prompt.name,
            "description": prompt.description,
            "category": prompt.category,
            "content": prompt.content,
            "version": prompt.version,
            "is_active": prompt.is_active,
            "usage_count": prompt.usage_count,
            "created_by_id": prompt.created_by_id,
            "created_at": prompt.created_at,
            "updated_at": prompt.updated_at,
        },
    )


async def update_prompt_service(prompt_id: str, payload: PromptUpdate, current_admin: Admin, db: Session):
    """
    Edits an existing prompt template (name, description, category, content, active status).
    Restricted to Super Admin role.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can edit system prompts",
        )

    target_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not target_prompt:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Target prompt not found",
        )

    if payload.name is not None:
        target_prompt.name = payload.name
    if payload.description is not None:
        target_prompt.description = payload.description
    if payload.category is not None:
        target_prompt.category = payload.category
    if payload.content is not None:
        target_prompt.content = payload.content
    if payload.is_active is not None:
        target_prompt.is_active = payload.is_active

    db.commit()
    db.refresh(target_prompt)

    return success_response(
        status_code=status.HTTP_200_OK,
        message=f"Prompt '{target_prompt.name}' updated successfully",
        data={
            "id": target_prompt.id,
            "name": target_prompt.name,
            "description": target_prompt.description,
            "category": target_prompt.category,
            "content": target_prompt.content,
            "version": target_prompt.version,
            "is_active": target_prompt.is_active,
            "usage_count": target_prompt.usage_count,
            "created_by_id": target_prompt.created_by_id,
            "created_at": target_prompt.created_at,
            "updated_at": target_prompt.updated_at,
        },
    )


async def activate_prompt_service(prompt_id: str, current_admin: Admin, db: Session):
    """
    Activates a target system prompt template.
    Restricted to Super Admin role.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can activate system prompts",
        )

    target_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not target_prompt:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Target prompt not found",
        )

    target_prompt.is_active = True
    db.commit()
    db.refresh(target_prompt)

    return success_response(
        status_code=status.HTTP_200_OK,
        message=f"Prompt '{target_prompt.name}' activated successfully",
        data={
            "id": target_prompt.id,
            "name": target_prompt.name,
            "version": target_prompt.version,
            "is_active": target_prompt.is_active,
        },
    )


async def deactivate_prompt_service(prompt_id: str, current_admin: Admin, db: Session):
    """
    Deactivates a target system prompt template.
    Restricted to Super Admin role.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can deactivate system prompts",
        )

    target_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not target_prompt:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Target prompt not found",
        )

    target_prompt.is_active = False
    db.commit()
    db.refresh(target_prompt)

    return success_response(
        status_code=status.HTTP_200_OK,
        message=f"Prompt '{target_prompt.name}' deactivated successfully",
        data={
            "id": target_prompt.id,
            "name": target_prompt.name,
            "version": target_prompt.version,
            "is_active": target_prompt.is_active,
        },
    )


async def duplicate_prompt_service(prompt_id: str, current_admin: Admin, db: Session):
    """
    Duplicates an existing prompt template into a new prompt entry.
    Restricted to Super Admin role.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can duplicate system prompts",
        )

    source_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not source_prompt:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Target prompt not found",
        )

    new_name = f"{source_prompt.name} (Copy)"
    existing_count = db.query(Prompt).filter(Prompt.name == new_name).count()

    duplicated = Prompt(
        name=new_name if existing_count == 0 else f"{new_name} v{existing_count + 1}",
        description=source_prompt.description,
        category=source_prompt.category,
        content=source_prompt.content,
        version=1,
        is_active=False,
        usage_count=0,
        created_by_id=current_admin.id,
    )
    db.add(duplicated)
    db.commit()
    db.refresh(duplicated)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message=f"Prompt '{source_prompt.name}' duplicated successfully",
        data={
            "id": duplicated.id,
            "name": duplicated.name,
            "description": duplicated.description,
            "category": duplicated.category,
            "content": duplicated.content,
            "version": duplicated.version,
            "is_active": duplicated.is_active,
            "usage_count": duplicated.usage_count,
            "created_by_id": duplicated.created_by_id,
            "created_at": duplicated.created_at,
            "updated_at": duplicated.updated_at,
        },
    )


async def delete_prompt_service(prompt_id: str, current_admin: Admin, db: Session):
    """
    Deletes a prompt template. Restricted to Super Admin role.
    """
    if current_admin.role not in [AdminRole.SUPER_ADMIN.value]:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only Super Admins can delete system prompts",
        )

    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Target prompt not found",
        )

    db.delete(prompt)
    db.commit()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="System prompt deleted successfully",
        data={"id": prompt_id},
    )
