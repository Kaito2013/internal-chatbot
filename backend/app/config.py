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
    LLM_PROVIDER: str = "openai"  # openai | minimax | anthropic | gemini | deepseek | litellm
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1  # Low temp for factual grounding
    MAX_TOKENS: int = 1000
    
    # Provider-specific API keys
    OPENAI_API_KEY: Optional[str] = None
    MINIMAX_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    
    # Minimax endpoint (OpenAI-compatible)
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"
    MINIMAX_GROUP_ID: Optional[str] = None
    
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

    # Database settings (PostgreSQL)
    POSTGRES_USER: str = "chatbot"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "chatbot_admin"
    DATABASE_ECHO: bool = False  # SQL echo mode for debugging

    # Admin credentials (thay đổi trong production!)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme"
    ADMIN_SECRET_KEY: str = "your-secret-key-change-in-production"  # JWT secret
    ADMIN_TOKEN_EXPIRE_HOURS: int = 24

    # File upload settings
    UPLOAD_DIR: str = "/tmp/chatbot_uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "txt,md,pdf,docx,html"  # Comma-separated

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()
