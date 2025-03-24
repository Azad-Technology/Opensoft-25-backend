from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import Optional
import os

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    MONGODB_URI: Optional[str] = os.getenv("MONGODB_URI")
    MONGODB_NAME: Optional[str] = os.getenv("MONGODB_NAME")
    
    # REDIS_URI: Optional[str] = os.getenv("REDIS_URI")
    
    GROQ_API_KEY1: Optional[str] = os.getenv("GROQ_API_KEY1")
    GROQ_API_KEY2: Optional[str] = os.getenv("GROQ_API_KEY2")
    
    GOOGLE_API_KEY1: Optional[str] = os.getenv("GOOGLE_API_KEY1")
    GOOGLE_API_KEY2: Optional[str] = os.getenv("GOOGLE_API_KEY2")
    
    ENC_SECRET_KEY: Optional[str] = os.getenv("ENC_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60*48
    
    
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

