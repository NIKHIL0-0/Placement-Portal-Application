import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///placement_portal.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    DAILY_REMINDER_HOUR = int(os.getenv("DAILY_REMINDER_HOUR", "9"))
    DAILY_REMINDER_MINUTE = int(os.getenv("DAILY_REMINDER_MINUTE", "0"))
    MONTHLY_REPORT_HOUR = int(os.getenv("MONTHLY_REPORT_HOUR", "8"))
    MONTHLY_REPORT_MINUTE = int(os.getenv("MONTHLY_REPORT_MINUTE", "0"))

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.mailtrap.io")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "noreply@placement.local")
    GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@institute.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-admin-password")

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads/resumes")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(5 * 1024 * 1024)))
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
