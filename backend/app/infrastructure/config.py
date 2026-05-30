from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    DB_URL: str = os.getenv("DB_URL", "mssql+aioodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\\SQLEXPRESS;DATABASE=energy_settlement;Trusted_Connection=yes;TrustServerCertificate=yes;")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key")

    class Config:
        env_file = ".env"

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
