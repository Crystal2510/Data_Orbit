from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    Each field maps to an environment variable of the same name (case-insensitive).
    """

    APP_NAME: str = Field(
        default="Data Dictionary Agent",
        description="Human-readable service name shown in logs and API docs"
    )
    DEBUG: bool = Field(
        default=False,
        description="Enables verbose tracebacks and Swagger UI unconditionally"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Python logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL"
    )

    
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Default SQLAlchemy connection URL. Optional — connections "
                    "are registered at runtime via POST /api/v1/connect."
    )

    
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key. If absent, PII detection uses heuristics only."
    )

    
    CHROMA_PERSIST_DIR: str = Field(
        default="./chroma_db",
        description="Directory where ChromaDB persists its vector index on disk."
    )

   
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   
        extra="ignore",         
    )


settings = Settings()