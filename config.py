import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    VK_TOKEN: str = os.getenv("VK_TOKEN", "")
    
    # Шлюз Polza.ai
    POLZA_API_KEY: str = os.getenv("POLZA_API_KEY", "")
    POLZA_BASE_URL: str = os.getenv("POLZA_BASE_URL", "https://api.polza.ai/v1")
    AI_MODEL: str = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

    # Baserow
    BASEROW_URL: str = os.getenv("BASEROW_URL", "https://baserow.example.com")
    BASEROW_TOKEN: str = os.getenv("BASEROW_TOKEN", "")
    BASEROW_TABLE_ID: int = int(os.getenv("BASEROW_TABLE_ID", "278"))

settings = Settings()