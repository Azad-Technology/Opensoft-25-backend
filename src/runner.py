from src.database.graph_db import Neo4j
from utils.api_key_rotate import APIKeyManager
from utils.config import settings

groq_api_manager = APIKeyManager(
    api_keys=[settings.GROQ_API_KEY1, settings.GROQ_API_KEY2, settings.GROQ_API_KEY3],
    rate_limit=30,
    cooldown_period=60
)

google_api_manager = APIKeyManager(
    api_keys=[settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2, settings.GOOGLE_API_KEY3],
    rate_limit=10,
    cooldown_period=60
)

graph_db = Neo4j(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)