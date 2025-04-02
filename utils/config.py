import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from pymongo import MongoClient

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    MONGODB_URI: str | None = os.getenv("MONGODB_URI")
    MONGODB_NAME: str | None = os.getenv("MONGODB_NAME")

    NEO4J_USER: str | None = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD: str | None = os.getenv("NEO4J_PASSWORD")

    # REDIS_URI: Optional[str] = os.getenv("REDIS_URI")

    GROQ_API_KEY1: str | None = os.getenv("GROQ_API_KEY1")
    GROQ_API_KEY2: str | None = os.getenv("GROQ_API_KEY2")
    GROQ_API_KEY3: str | None = os.getenv("GROQ_API_KEY3")

    GOOGLE_API_KEY1: str | None = os.getenv("GOOGLE_API_KEY1")
    GOOGLE_API_KEY2: str | None = os.getenv("GOOGLE_API_KEY2")
    GOOGLE_API_KEY3: str | None = os.getenv("GOOGLE_API_KEY3")
    GOOGLE_API_KEY4: str | None = os.getenv("GOOGLE_API_KEY4")
    GOOGLE_API_KEY5: str | None = os.getenv("GOOGLE_API_KEY5")
    GOOGLE_API_KEY6: str | None = os.getenv("GOOGLE_API_KEY6")
    GOOGLE_API_KEY7: str | None = os.getenv("GOOGLE_API_KEY7")
    GOOGLE_API_KEY8: str | None = os.getenv("GOOGLE_API_KEY8")
    GOOGLE_API_KEY9: str | None = os.getenv("GOOGLE_API_KEY9")
    GOOGLE_API_KEY10: str | None = os.getenv("GOOGLE_API_KEY10")
    GOOGLE_API_KEY11: str | None = os.getenv("GOOGLE_API_KEY11")
    GOOGLE_API_KEY12: str | None = os.getenv("GOOGLE_API_KEY12")
    GOOGLE_API_KEY13: str | None = os.getenv("GOOGLE_API_KEY13")
    GOOGLE_API_KEY14: str | None = os.getenv("GOOGLE_API_KEY14")

    ENC_SECRET_KEY: str | None = os.getenv("ENC_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 48


settings = Settings()

# Create database clients using the updated settings
database_client = AsyncIOMotorClient(settings.MONGODB_URI)
database = database_client.get_database(settings.MONGODB_NAME)

pymongo_client = MongoClient(settings.MONGODB_URI)
pymongo_db = pymongo_client.get_database(settings.MONGODB_NAME)


def get_async_database():
    return database


def get_sync_database():
    return pymongo_db
