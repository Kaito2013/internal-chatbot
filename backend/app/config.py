"""
Cấu hình ứng dụng sử dụng Pydantic Settings.
Đọc biến môi trường từ .env file.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Cấu hình ứng dụng."""

    # Vector DB settings
    VECTOR_DB_TYPE: str = "qdrant"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "documents"

    # Embedding settings
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    # Chunking settings
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # LLM settings (Agentic Layer)
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1  # Low temp for factual grounding
    MAX_TOKENS: int = 1000
    LITE_LLM_API_BASE: Optional[str] = None  # Proxy URL cho LiteLLM

    # CRM settings
    CRM_PROVIDER: str = "generic"
    CRM_API_URL: str = "https://api.example.com"
    CRM_API_KEY: Optional[str] = None
    CRM_USE_MOCK: bool = True  # Dùng mock CRM trong development

    # Agent settings
    AGENT_MAX_TOOL_CALLS: int = 5
    AGENT_TOOL_TIMEOUT: float = 30.0
    AGENT_MAX_CONTEXT_MESSAGES: int = 20

    # Backend settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "*"  # Comma-separated origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()
