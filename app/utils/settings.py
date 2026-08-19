from pydantic_settings import BaseSettings
from decouple import config
from pathlib import Path

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    """Class to hold application's config values."""

    SECRET_KEY: str = config("SECRET_KEY")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRES_IN: int = config("ACCESS_TOKEN_EXPIRES_IN")
    REFRESH_TOKEN_EXPIRES_IN: int = config("REFRESH_TOKEN_EXPIRES_IN")

    # Database configurations
    DB_HOST: str = config("DB_HOST")
    DB_PORT: int = config("DB_PORT", cast=int)
    DB_USER: str = config("DB_USER")
    DB_PASSWORD: str = config("DB_PASSWORD")
    DB_NAME: str = config("DB_NAME")
    DB_TYPE: str = config("DB_TYPE")
    DB_URL: str = config("DB_URL")

    BASE_DIR:str = config("BASE_DIR")
    
    # Paystack configurations
    # PAYSTACK_SECRET_KEY: str = config("PAYSTACK_SECRET_KEY")

    # Firebase / Google Auth
    # SERVICE_ACCOUNT_JSON: str = config("SERVICE_ACCOUNT_JSON")
    
    # Cloudinary configurations
    # CLOUDINARY_CLOUD_NAME: str = config("CLOUDINARY_CLOUD_NAME")
    # CLOUDINARY_API_KEY: str = config("CLOUDINARY_API_KEY")
    # CLOUDINARY_API_SECRET: str = config("CLOUDINARY_API_SECRET")

    # REDIS configurations
    # REDIS_HOST: str = config("REDIS_HOST")
    # REDIS_PORT: str = config("REDIS_PORT")
    # REDIS_URL: str = config("REDIS_URL")
    # REDIS_PASSWORD: str = config("REDIS_PASSWORD")
    
    # Email configurations (Resend)
    # RESEND_API_KEY: str = config("RESEND_API_KEY")
    # FROM_EMAIL: str = config("FROM_EMAIL")

    # Dashboard
    # DASHBOARD: str = config("DASHBOARD")
    
settings = Settings()