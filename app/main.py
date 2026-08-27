from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router.admin.auth import admin_auth_router
from app.api.router.admin.submission import admin_submission_router
from app.api.router.admin.dashboard import admin_dashboard_router
from app.api.router.admin.staff import admin_staff_router
from app.api.router.admin.task import admin_task_router
from app.api.router.admin.prompt import admin_prompt_router
from app.api.router.admin.ai import admin_ai_router
from app.api.router.admin.ws import admin_ws_router
from app.api.router.admin.document import admin_document_router
from app.api.router.client.submission import client_router
from app.api.router.client.upload import upload_router
from app.api.router.client.ws import client_ws_router
from app.api.router.client.document import client_document_router

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "https://ai-cv-generator-fe-1.onrender.com",
    "https://admin-ai-cv-generator-fe.onrender.com",
    "https://admin-ai-cv-generator-fe-1.onrender.com",
    "https://ai-cv-generator-fe.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_auth_router, prefix="/api/v1/admin")
app.include_router(admin_submission_router, prefix="/api/v1/admin")
app.include_router(admin_dashboard_router, prefix="/api/v1/admin")
app.include_router(admin_staff_router, prefix="/api/v1/admin")
app.include_router(admin_task_router, prefix="/api/v1/admin")
app.include_router(admin_prompt_router, prefix="/api/v1/admin")
app.include_router(admin_ai_router, prefix="/api/v1/admin")
app.include_router(admin_ws_router, prefix="/api/v1/admin")   # WS: /api/v1/admin/submissions/{id}/ws
app.include_router(admin_document_router, prefix="/api/v1/admin")
app.include_router(client_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1/public")
app.include_router(client_ws_router, prefix="/api/v1")        # WS: /api/v1/public/submissions/{id}/ws
app.include_router(client_document_router, prefix="/api/v1")


@app.get("/health", tags=["HealthCheck"])
def health():
    return {"status": "healthy", "message": "Server is running smoothly"}

@app.get("/")
def root():
    return {"message": "Welcome to AI-CV-Generator API"}