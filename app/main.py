from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router.admin.auth import admin_auth_router

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_auth_router, prefix="/api/v1/admin")

@app.get("/")
def root():
    return {"message": "Welcome to AI-CV-Generator API"}