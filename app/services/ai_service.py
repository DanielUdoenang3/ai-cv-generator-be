import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import status
import httpx
from sqlalchemy.orm import Session

from app.models.submissions import Submission
from app.models.chats import Conversation, Message
from app.models.admins import Admin
from app.models.prompts import Prompt
from app.models.ai_generations import AiGeneration
from app.models.activities import SubmissionActivity
from app.models.enums import AdminRole, AiGenerationStatus, SubmissionStatus, MessageSenderType
from app.schema.ai import CvGenerateRequest, StructuredCvData, StructuredCvPersonal, StructuredCvExperience, StructuredCvEducation, StructuredCvProject
from app.services.admin.prompt import get_active_master_prompt, seed_default_prompts_if_empty
from app.utils.settings import settings
from app.utils.custom_response import success_response, error_response
from app.utils.websocket_manager import manager

logger = logging.getLogger(__name__)


def build_generation_prompt_context(
    submission: Submission,
    messages: List[Message],
    custom_instructions: Optional[str] = None,
) -> str:
    """
    Combines client submission data, job description, client-admin chat transcript,
    and custom admin instructions into a unified prompt context.
    """
    client = submission.client
    client_name = f"{client.first_name} {client.last_name}" if client else "Client"

    context_parts = []
    context_parts.append("=== CLIENT INFORMATION ===")
    context_parts.append(f"Full Name: {client_name}")
    if client:
        context_parts.append(f"Email: {client.email}")
        if client.phone:
            context_parts.append(f"Phone: {client.phone}")

    context_parts.append(f"Target Position: {submission.target_position or 'Not specified'}")
    if submission.target_company:
        context_parts.append(f"Target Company: {submission.target_company}")

    if submission.job_description:
        context_parts.append(f"\n=== TARGET JOB DESCRIPTION ===\n{submission.job_description}")

    if submission.raw_data:
        context_parts.append(f"\n=== SUBMITTED RAW CV / BACKGROUND DATA ===\n{submission.raw_data}")

    # Add chat transcript if available
    if messages:
        context_parts.append("\n=== CLIENT-ADMIN CHAT TRANSCRIPT (CRITICAL ADDITIONAL METRICS & CONTEXT) ===")
        for msg in messages:
            sender_label = "CLIENT" if msg.sender_type == MessageSenderType.CLIENT.value else "ADMIN"
            context_parts.append(f"[{sender_label}]: {msg.message}")

    if custom_instructions and custom_instructions.strip():
        context_parts.append(f"\n=== ADMIN SPECIAL INSTRUCTIONS ===\n{custom_instructions.strip()}")

    return "\n".join(context_parts)


def _generate_mock_structured_cv(submission: Submission, custom_instructions: Optional[str] = None) -> dict:
    """Fallback generator for offline/testing/dev environments when no live API key is configured."""
    client = submission.client
    client_name = f"{client.first_name} {client.last_name}" if client else "Robert Kim"
    target_role = submission.target_position or "Senior Backend Engineer"
    target_company = submission.target_company or "TechCorp"

    extra_note = ""
    if custom_instructions:
        extra_note = f" Highlighted note: {custom_instructions}"

    return {
        "personal_info": {
            "full_name": client_name,
            "email": client.email if client else "robert.kim@example.com",
            "phone": client.phone if client and client.phone else "+1 (555) 234-5678",
            "location": "San Francisco, CA",
            "linkedin": f"linkedin.com/in/{client_name.lower().replace(' ', '')}",
            "portfolio": "github.com/dev-lead",
            "target_role": target_role,
        },
        "professional_summary": (
            f"Results-driven {target_role} with 7+ years of experience designing scalable microservices, "
            f"high-throughput REST/gRPC APIs, and cloud infrastructure. Demonstrated success optimizing system "
            f"performance for enterprise platforms like {target_company}. Reduced API response latency by 40% and "
            f"scaled backend architecture to reliably handle 5M+ daily active requests.{extra_note}"
        ),
        "work_experience": [
            {
                "job_title": target_role,
                "company": target_company,
                "location": "San Francisco, CA",
                "start_date": "2022-03",
                "end_date": "Present",
                "is_current": True,
                "bullet_points": [
                    "Architected high-concurrency event-driven backend services handling over 5 million API requests daily with 99.99% uptime.",
                    "Optimized PostgreSQL database query indexing and Redis caching layer, successfully reducing P99 latency by 40%.",
                    "Led cross-functional team of 6 engineers in migrating monolithic legacy service to FastAPI microservices.",
                    "Implemented CI/CD automated test pipelines reducing deployment rollback rates by 35%.",
                ],
            },
            {
                "job_title": "Software Engineer",
                "company": "DataTech Solutions",
                "location": "San Jose, CA",
                "start_date": "2019-06",
                "end_date": "2022-02",
                "is_current": False,
                "bullet_points": [
                    "Developed asynchronous RESTful endpoints using Python and SQLAlchemy for real-time analytics dashboard.",
                    "Configured Dockerized container infrastructure and Kubernetes deployment manifests.",
                ],
            },
        ],
        "skills": {
            "Languages & Frameworks": ["Python", "FastAPI", "Go", "SQL", "TypeScript", "Node.js"],
            "Databases & Storage": ["PostgreSQL", "Redis", "MongoDB", "Alembic"],
            "Cloud & DevOps": ["AWS (EC2, S3, RDS)", "Docker", "Kubernetes", "CI/CD", "Nginx"],
            "Architecture & Tools": ["Microservices", "RESTful APIs", "WebSockets", "Git", "pytest"],
        },
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "University of California, Berkeley",
                "location": "Berkeley, CA",
                "graduation_year": "2019",
                "honors": "Magna Cum Laude",
            }
        ],
        "projects": [
            {
                "title": "High-Throughput Distributed Rate Limiter",
                "description": "Engineered sliding-window rate limiter using Redis and Go capable of processing 50k requests/sec.",
                "tech_stack": ["Go", "Redis", "Docker"],
                "link": "github.com/example/rate-limiter",
            }
        ],
        "certifications": [
            "AWS Certified Solutions Architect – Associate",
            "Certified Kubernetes Administrator (CKA)",
        ],
    }


async def _call_openai(openai_key: str, model_name: Optional[str], user_prompt: str, system_prompt: str) -> Dict[str, Any]:
    """Internal: Execute a live OpenAI API call."""
    target_model = model_name or settings.OPENAI_MODEL
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(f"OpenAI API Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        in_tokens = usage.get("prompt_tokens", 0)
        out_tokens = usage.get("completion_tokens", 0)
        cost = round((in_tokens * 0.0000025) + (out_tokens * 0.000010), 6)

        return {
            "structured_cv": json.loads(content),
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost": cost,
            "model_used": target_model,
            "provider_used": "openai",
            "is_mock": False,
        }


async def _call_gemini(gemini_key: str, model_name: Optional[str], user_prompt: str, system_prompt: str) -> Dict[str, Any]:
    """Internal: Execute a live Gemini API call."""
    target_model = model_name or settings.GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {
                "parts": [
                    {"text": f"System Instructions:\n{system_prompt}\n\nUser Context:\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(f"Gemini API Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise Exception("Gemini returned empty candidates")

        content_text = candidates[0]["content"]["parts"][0]["text"]
        usage_meta = data.get("usageMetadata", {})
        in_tokens = usage_meta.get("promptTokenCount", 0)
        out_tokens = usage_meta.get("candidatesTokenCount", 0)
        cost = round((in_tokens * 0.0000015) + (out_tokens * 0.000005), 6)

        return {
            "structured_cv": json.loads(content_text),
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost": cost,
            "model_used": target_model,
            "provider_used": "gemini",
            "is_mock": False,
        }


async def call_llm_provider(
    provider: str,
    model_name: Optional[str],
    user_prompt: str,
    system_prompt: str,
) -> Dict[str, Any]:
    """
    Calls the appropriate LLM provider (OpenAI or Gemini) with smart fallback.

    Fallback rules:
    - If the requested provider's API key is available → use it directly.
    - If the requested provider's key is missing but the other provider's key
      IS available → silently fall back to that provider.
    - If neither key is configured → raise a user-friendly error immediately.
      (No silent mock data in production.)
    """
    requested = provider.lower()
    if requested not in ("openai", "gemini"):
        raise ValueError(f"Unsupported provider: '{requested}'. Must be 'openai' or 'gemini'.")

    openai_key = settings.OPENAI_API_KEY
    gemini_key = settings.GEMINI_API_KEY

    # ── Guard: no keys at all ────────────────────────────────────────────────
    if not openai_key and not gemini_key:
        raise Exception(
            "No AI provider API key is configured. "
            "Please add OPENAI_API_KEY or GEMINI_API_KEY to your environment variables "
            "and redeploy the service."
        )

    # ── Resolve the actual provider to use after smart fallback ─────────────
    if requested == "openai":
        if openai_key:
            actual = "openai"
        else:
            # OpenAI key missing → fall back to Gemini
            logger.warning(
                "OPENAI_API_KEY is not configured. "
                "Falling back to Gemini for this generation."
            )
            actual = "gemini"
    else:  # requested == "gemini"
        if gemini_key:
            actual = "gemini"
        else:
            # Gemini key missing → fall back to OpenAI
            logger.warning(
                "GEMINI_API_KEY is not configured. "
                "Falling back to OpenAI for this generation."
            )
            actual = "openai"

    # ── Execute the resolved provider call ───────────────────────────────────
    if actual == "openai":
        result = await _call_openai(openai_key, model_name, user_prompt, system_prompt)
    else:
        result = await _call_gemini(gemini_key, model_name, user_prompt, system_prompt)

    # Surface fallback info in logs so it's visible in server output
    if actual != requested:
        logger.info(
            f"AI generation used '{actual}' (requested: '{requested}') "
            f"— model: {result['model_used']}"
        )

    return result


async def generate_cv_service(
    submission_id: str,
    payload: CvGenerateRequest,
    current_admin: Admin,
    db: Session,
):
    """
    Executes the full CV Generation Pipeline:
    1. Validates submission & enforces sub-admin RBAC.
    2. Fetches active System Prompt & client chat messages context.
    3. Calls LLM provider (OpenAI or Gemini) or mock generator.
    4. Parses & validates returned output against StructuredCvData Pydantic schema.
    5. Records metadata in ai_generations table.
    6. Updates submission status to 'review' / 'ai_generated'.
    7. Broadcasts WebSocket event.
    """
    # 1. Fetch submission
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    # Sub-admin RBAC check: sub-admins can only generate for assigned submissions
    is_restricted = current_admin.role in [AdminRole.SUB_ADMIN.value]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to generate CV for this submission",
        )

def select_smart_prompt_for_submission(
    submission: Submission,
    prompt_id: Optional[str],
    db: Session,
) -> Optional[Prompt]:
    """
    Smart Prompt Selection Hierarchy:
    1. Explicit prompt_id passed by admin (Highest Priority).
    2. Category & Role matching against submission.target_position among Active Prompts.
    3. Default active prompt fallback.
    """
    if prompt_id:
        return db.query(Prompt).filter(Prompt.id == prompt_id).first()

    # Query active prompts
    active_prompts = db.query(Prompt).filter(Prompt.is_active == True).all()
    if not active_prompts:
        seed_default_prompts_if_empty(db)
        active_prompts = db.query(Prompt).filter(Prompt.is_active == True).all()

    if not active_prompts:
        return get_active_master_prompt(db)

    target_pos = (submission.target_position or "").lower()

    if target_pos:
        # Phase 1: Dynamic direct match against prompt category or prompt name
        for prompt in active_prompts:
            cat = (prompt.category or "").lower()
            name = (prompt.name or "").lower()
            if cat and cat in target_pos:
                return prompt
            if name and name in target_pos:
                return prompt

        # Phase 2: Expanded broad keyword dictionaries for role categories
        tech_keywords = [
            "software", "engineer", "developer", "backend", "frontend", "fullstack", "full-stack",
            "tech", "technology", "data", "database", "dba", "code", "coder", "programming", "programmer",
            "devops", "sre", "cloud", "sysadmin", "system", "systems", "network", "security", "cybersecurity",
            "qa", "test", "tester", "automation", "ai", "ml", "machine learning", "architect", "web",
            "webmaster", "mobile", "ios", "android", "firmware", "embedded", "technical"
        ]
        product_keywords = [
            "product", "pm", "scrum", "agile", "kanban", "sprint", "project manager", "project management",
            "program manager", "owner", "producer", "business analyst", "ba", "delivery manager",
            "operations manager", "ops manager", "product owner", "product lead"
        ]
        exec_keywords = [
            "executive", "director", "vp", "vice president", "chief", "cto", "ceo", "cfo", "coo", "cmo",
            "cpo", "cio", "ciso", "head of", "lead", "principal", "founder", "co-founder", "managing director",
            "partner", "general manager", "gm", "president", "chairman"
        ]
        marketing_keywords = [
            "marketing", "marketer", "growth", "seo", "sem", "ppc", "content", "copywriter", "brand",
            "branding", "social media", "smm", "public relations", "pr", "communications", "digital marketing",
            "email marketing", "sales", "account executive", "bizdev", "business development", "customer success",
            "demand gen", "growth hacker"
        ]

        desired_category = None
        if any(kw in target_pos for kw in tech_keywords):
            desired_category = "technology"
        elif any(kw in target_pos for kw in product_keywords):
            desired_category = "product"
        elif any(kw in target_pos for kw in exec_keywords):
            desired_category = "executive"
        elif any(kw in target_pos for kw in marketing_keywords):
            desired_category = "marketing"

        if desired_category:
            for prompt in active_prompts:
                cat = (prompt.category or "").lower()
                name = (prompt.name or "").lower()
                if desired_category in cat or desired_category in name:
                    return prompt

    return active_prompts[0]


async def generate_cv_service(
    submission_id: str,
    payload: CvGenerateRequest,
    current_admin: Admin,
    db: Session,
):
    """
    Executes the full CV Generation Pipeline:
    1. Validates submission & enforces sub-admin RBAC.
    2. Fetches active System Prompt using Smart Role Matching & client chat messages context.
    3. Calls LLM provider (OpenAI or Gemini) or mock generator.
    4. Parses & validates returned output against StructuredCvData Pydantic schema.
    5. Records metadata in ai_generations table & increments prompt usage count.
    6. Updates submission status to 'review' / 'ai_generated'.
    7. Broadcasts WebSocket event.
    """
    # 1. Fetch submission
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    # Sub-admin RBAC check: sub-admins can only generate for assigned submissions
    is_restricted = current_admin.role in [AdminRole.SUB_ADMIN.value]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to generate CV for this submission",
        )

    # 2. Smart System Prompt Selection
    master_prompt_obj = select_smart_prompt_for_submission(
        submission=submission,
        prompt_id=payload.prompt_id,
        db=db,
    )
    if not master_prompt_obj:
        master_prompt_obj = get_active_master_prompt(db)

    system_prompt_text = master_prompt_obj.content

    # 3. Fetch chat transcript if requested
    messages = []
    if payload.include_chat_history:
        conversation = db.query(Conversation).filter(Conversation.submission_id == submission_id).first()
        if conversation:
            messages = conversation.messages or []

    # Build context string
    user_context_prompt = build_generation_prompt_context(
        submission=submission,
        messages=messages,
        custom_instructions=payload.custom_instructions,
    )

    # 4. Call LLM Service
    try:
        llm_result = await call_llm_provider(
            provider=payload.provider,
            model_name=payload.model,
            user_prompt=user_context_prompt,
            system_prompt=system_prompt_text,
        )
    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"AI Generation Failed: {error_msg}")

        # Detect "no API keys configured" and return a clear 503 instead of a generic 500
        no_keys_configured = "No AI provider API key is configured" in error_msg
        http_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE if no_keys_configured
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        user_message = (
            error_msg if no_keys_configured
            else f"AI generation failed: {error_msg}"
        )

        # Log failure record in DB
        failed_generation = AiGeneration(
            submission_id=submission_id,
            model=payload.model or "unknown",
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
            status=AiGenerationStatus.FAILED.value,
            error_message=error_msg,
        )
        db.add(failed_generation)
        db.commit()
        return error_response(
            status_code=http_status,
            message=user_message,
        )

    # Populate mock data if in mock mode
    if llm_result.get("is_mock"):
        structured_dict = _generate_mock_structured_cv(submission, payload.custom_instructions)
    else:
        structured_dict = llm_result["structured_cv"]

    # Validate against StructuredCvData schema
    try:
        structured_cv_obj = StructuredCvData.model_validate(structured_dict)
    except Exception as val_err:
        logger.error(f"JSON validation error: {str(val_err)}")

        # Log failed schema validation
        failed_gen = AiGeneration(
            submission_id=submission_id,
            model=llm_result["model_used"],
            input_tokens=llm_result["input_tokens"],
            output_tokens=llm_result["output_tokens"],
            cost=llm_result["cost"],
            status=AiGenerationStatus.FAILED.value,
            error_message=f"Output failed JSON schema validation: {str(val_err)}",
        )
        db.add(failed_gen)
        db.commit()
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"AI output failed CV JSON schema validation: {str(val_err)}",
        )

    # 5. Log successful AiGeneration record & increment prompt usage count
    ai_gen_record = AiGeneration(
        submission_id=submission_id,
        model=llm_result["model_used"],
        input_tokens=llm_result["input_tokens"],
        output_tokens=llm_result["output_tokens"],
        cost=llm_result["cost"],
        status=AiGenerationStatus.SUCCESS.value,
        error_message=None,
        structured_cv_json=structured_cv_obj.model_dump(),  # Persist for document rendering
    )
    db.add(ai_gen_record)

    # Increment usage counter on prompt
    master_prompt_obj.usage_count = (master_prompt_obj.usage_count or 0) + 1

    # 6. Update Submission status & audit activity
    submission.status = SubmissionStatus.REVIEW.value
    activity = SubmissionActivity(
        submission_id=submission.id,
        activity_type="status_changed",
        title="AI CV Generated",
        description=f"Structured CV generated using model '{llm_result['model_used']}' by {current_admin.first_name} {current_admin.last_name}",
        actor_id=current_admin.id,
    )
    db.add(activity)

    db.commit()
    db.refresh(ai_gen_record)

    # 7. Broadcast WebSocket event
    await manager.broadcast_to_submission(submission_id, {
        "event": "cv_generated",
        "data": {
            "submission_id": submission_id,
            "ai_generation_id": ai_gen_record.id,
            "model": ai_gen_record.model,
            "generated_by": f"{current_admin.first_name} {current_admin.last_name}",
        },
    })

    # Determine actual provider used (may differ from requested due to smart fallback)
    actual_provider = llm_result.get("provider_used", payload.provider)
    provider_note = (
        f"Requested '{payload.provider}', used '{actual_provider}' (smart fallback — "
        f"'{payload.provider}' API key not configured)."
        if actual_provider != payload.provider
        else None
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Structured CV generated successfully",
        data={
            "ai_generation_id": ai_gen_record.id,
            "submission_id": submission_id,
            "model": ai_gen_record.model,
            "provider_requested": payload.provider,
            "provider_used": actual_provider,
            **({"provider_fallback_note": provider_note} if provider_note else {}),
            "input_tokens": ai_gen_record.input_tokens,
            "output_tokens": ai_gen_record.output_tokens,
            "cost": ai_gen_record.cost,
            "status": ai_gen_record.status,
            "structured_cv": structured_cv_obj.model_dump(),
        },
    )


async def get_submission_generations_service(
    submission_id: str,
    current_admin: Admin,
    db: Session,
):
    """
    Returns the log of AI generations (tokens, cost, model, status) for a specific submission.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    is_restricted = current_admin.role in [AdminRole.SUB_ADMIN.value]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to view generation history for this submission",
        )

    generations = db.query(AiGeneration).filter(
        AiGeneration.submission_id == submission_id
    ).order_by(AiGeneration.created_at.desc()).all()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="AI generation history fetched successfully",
        data=[
            {
                "id": g.id,
                "submission_id": g.submission_id,
                "model": g.model,
                "input_tokens": g.input_tokens,
                "output_tokens": g.output_tokens,
                "cost": g.cost,
                "status": g.status,
                "error_message": g.error_message,
                "created_at": g.created_at,
            }
            for g in generations
        ],
    )
