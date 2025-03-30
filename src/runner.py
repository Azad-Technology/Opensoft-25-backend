from src.database.graph_db import Neo4j
from utils.api_key_rotate import APIKeyManager
from utils.config import settings

groq_api_manager = APIKeyManager(
    api_keys=[settings.GROQ_API_KEY1, settings.GROQ_API_KEY2, settings.GROQ_API_KEY3],
    rate_limit=30,
    cooldown_period=60
)

google_api_manager = APIKeyManager(
    api_keys=[settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2, settings.GOOGLE_API_KEY3, settings.GOOGLE_API_KEY4, settings.GOOGLE_API_KEY5, settings.GOOGLE_API_KEY6, settings.GOOGLE_API_KEY7, settings.GOOGLE_API_KEY8, settings.GOOGLE_API_KEY9, settings.GOOGLE_API_KEY10, settings.GOOGLE_API_KEY11, settings.GOOGLE_API_KEY12, settings.GOOGLE_API_KEY13],
    rate_limit=10,
    cooldown_period=60
)

graph_db = Neo4j("neo4j+s://419ac377.databases.neo4j.io", settings.NEO4J_USER, settings.NEO4J_PASSWORD)