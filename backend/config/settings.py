from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Data Dictionary Agent"
    DEBUG: bool = False

    DATABASE_URL: Optional[str] = None

    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    CHROMA_PERSIST_DIR: str = "./chroma_db"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()