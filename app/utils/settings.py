import os
from pydantic_settings import BaseSettings
from decouple import config
from pathlib import Path

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """Class to hold application's config values with robust production defaults."""

    SECRET_KEY: str = config("SECRET_KEY", default="super-secret-key-change-in-production")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRES_IN: int = config("ACCESS_TOKEN_EXPIRES_IN", cast=int, default=86400)
    REFRESH_TOKEN_EXPIRES_IN: int = config("REFRESH_TOKEN_EXPIRES_IN", cast=int, default=604800)

    # Database configurations
    DB_HOST: str = config("DB_HOST", default="localhost")
    DB_PORT: int = config("DB_PORT", cast=int, default=5432)
    DB_USER: str = config("DB_USER", default="postgres")
    DB_PASSWORD: str = config("DB_PASSWORD", default="postgres")
    DB_NAME: str = config("DB_NAME", default="ai_cv_generator")
    DB_TYPE: str = config("DB_TYPE", default="postgresql")
    
    # Priority for single connection string: DB_URL -> DATABASE_URL -> POSTGRES_URL -> DATABASE_PUBLIC_URL
    DB_URL: str = config("DB_URL", default=config("DATABASE_URL", default=config("POSTGRES_URL", default="")))

    BASE_DIR: str = config("BASE_DIR", default=str(BASE_DIR))

    # Cloudinary configurations
    CLOUDINARY_CLOUD_NAME: str = config("CLOUDINARY_CLOUD_NAME", default="")
    CLOUDINARY_API_KEY: str = config("CLOUDINARY_API_KEY", default="")
    CLOUDINARY_API_SECRET: str = config("CLOUDINARY_API_SECRET", default="")
    CLOUDINARY_URL: str = config("CLOUDINARY_URL", default="")

    # REDIS configurations
    REDIS_HOST: str = config("REDIS_HOST", default="localhost")
    REDIS_PORT: str = config("REDIS_PORT", default="6379")
    REDIS_URL: str = config("REDIS_URL", default="")
    REDIS_PASSWORD: str = config("REDIS_PASSWORD", default="")

    # WebSocket Pub/Sub backend — "memory" (default, single-worker) | "redis" (multi-worker, Hetzner)
    WS_BACKEND: str = config("WS_BACKEND", default="memory")

    # Email configurations (Resend)
    RESEND_API_KEY: str = config("RESEND_API_KEY", default="")
    FROM_EMAIL: str = config("FROM_EMAIL", default="noreply@example.com")

    # Dashboard
    DASHBOARD: str = config("DASHBOARD", default="http://localhost:3000")

    # AI-CV-GENERATOR
    OPENAI_API_KEY: str = config("OPENAI_API_KEY")
    OPENAI_MODEL: str = config("OPENAI_MODEL")
    GEMINI_API_KEY: str = config("GEMINI_API_KEY")
    GEMINI_MODEL: str = config("GEMINI_MODEL", default="gemini-1.5-flash")

    # Cloudinary
    CLOUDINARY_URL: str = config("CLOUDINARY_URL", default="")

settings = Settings()