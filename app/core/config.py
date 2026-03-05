import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    app_name = os.getenv("APP_NAME", "")
    app_env = os.getenv("APP_ENV", "")
    app_api_key = os.getenv("APP_API_KEY", "")
    database_url = os.getenv("DB_URL", "")


settings = Settings()
