"""
Internal Chatbot Backend - FastAPI Entry Point
===============================================
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import get_settings
from .rag.pipeline import RAGPipeline
from .rag.retriever import HybridRetriever
from .rag.embedding import AsyncEmbeddingService
from .db.vector import VectorDB
from .db.database import init_db, get_db_context
from .agentic.agent import Agent, AgentMode
from .agentic.tools import ToolRegistry
from .crm.factory import CRMClientFactory
from .admin import router as admin_router
from .admin.service import log_chat_interaction, get_or_create_session

# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Lifespan
# ============================================================================

settings = get_settings()
rag_pipeline: Optional[RAGPipeline] = None
agent: Optional[Agent] = None


# ============================================================================
# LLM Client Factory
# ============================================================================

def create_llm_client(settings) -> Optional[Any]:
    """
    Tạo LLM client dựa trên provider được cấu hình.
    
    Providers:
    - openai: OpenAI API (GPT-4, GPT-3.5)
    - minimax: Minimax API (OpenAI-compatible)
    - anthropic: Anthropic API (Claude)
    - deepseek: DeepSeek API
    - mock: Mock client cho development
    """
    provider = settings.LLM_PROVIDER.lower()
    
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("openai package not installed, using mock LLM")
        return None
    
    if provider == "openai":
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, using mock LLM")
            return None
        return AsyncOpenAI(api_key=settings.openai_api_key)
    
    elif provider == "minimax":
        if not settings.minimax_api_key:
            logger.warning("MINIMAX_API_KEY not set, using mock LLM")
            return None
        # Minimax uses OpenAI-compatible endpoint
        client = AsyncOpenAI(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        )
        return client
    
    elif provider == "deepseek":
        if not settings.deepseek_api_key:
            logger.warning("DEEPSEEK_API_KEY not set, using mock LLM")
            return None
        return AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com/v1",
        )
    
    elif provider == "anthropic":
        # Anthropic uses different client
        try:
            from anthropic import AsyncAnthropic
            if not settings.anthropic_api_key:
                logger.warning("ANTHROPIC_API_KEY not set, using mock LLM")
                return None
            return AsyncAnthropic(api_key=settings.anthropic_api_key)
        except ImportError:
            logger.warning("anthropic package not installed, using mock LLM")
            return None
    
    elif provider == "mock":
        logger.info("Using mock LLM client")
        return None
    
    else:
        logger.warning(f"Unknown LLM provider '{provider}', using mock")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo resources khi app start, cleanup khi app shutdown."""
    global rag_pipeline, agent
    
    logger.info("Initializing services...")
    
    # Initialize PostgreSQL database
    logger.info("Initializing PostgreSQL database...")
    try:
        await init_db()
        logger.info("Database tables created successfully")
        
        # Create default admin user
        async with get_db_context() as db:
            from .admin.service import ensure_default_admin
            admin, created = await ensure_default_admin(db)
            if created:
                logger.info(f"Created default admin user: {admin.username}")
            else:
                logger.info(f"Admin user already exists: {admin.username}")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        # Continue without database - some features won't work
    
    # Initialize VectorDB
    vector_db = VectorDB(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        vector_size=settings.embedding_dim,
    )
    
    # Initialize Embedding service
    embedding_service = AsyncEmbeddingService(
        model=settings.embedding_model,
        api_key=settings.openai_api_key or None,
    )
    
    # Initialize RAG Pipeline
    rag_pipeline = RAGPipeline(
        vector_db=vector_db,
        embedding_service=embedding_service,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    
    # Initialize CRM Client
    crm_client = CRMClientFactory.create(
        provider=settings.crm_provider,
        api_url=settings.crm_api_url,
        api_key=settings.crm_api_key,
        use_mock=settings.crm_use_mock,
    )
    
    # Initialize Tool Registry
    tool_registry = ToolRegistry()

    # Initialize LLM Client (theo provider)
    llm_client = create_llm_client(settings)

    # Initialize Agent
    agent = Agent(
        rag_pipeline=rag_pipeline,
        crm_client=crm_client,
        tool_registry=tool_registry,
        llm_client=llm_client,
        llm_model=settings.llm_model,
        llm_temperature=settings.llm_temperature,
        max_tokens=settings.max_tokens,
    )
    
    logger.info("Services initialized successfully")
    
    yield
    
    logger.info("Shutting down...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Internal Chatbot API",
    description="RAG-powered chatbot with CRM integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Admin routes
app.include_router(admin_router)

# ============================================================================
# Schemas
# ============================================================================

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from client")
    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    email: Optional[str] = Field(None, description="User email")
    mode: Optional[str] = Field("HYBRID", description="Agent mode: CHAT, TOOL_USE, REASONING, HYBRID")


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)
    used_crm: bool = False
    session_id: str
    mode: str


class IngestRequest(BaseModel):
    source: str = Field(..., description="Directory path or file path to ingest")
    recreate: bool = Field(False, description="Recreate collection before ingesting")
    chunk_strategy: Optional[str] = Field("recursive", description="Chunking strategy")
    batch_size: Optional[int] = Field(32, description="Batch size for embedding")


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int
    time_seconds: float


class HealthResponse(BaseModel):
    status: str
    vector_db: str
    collection: str
    documents_count: int
    llm_model: str


# ============================================================================
# Dependencies
# ============================================================================

def get_rag_pipeline() -> RAGPipeline:
    if rag_pipeline is None:
        raise HTTPException(503, "RAG pipeline not initialized")
    return rag_pipeline


def get_agent() -> Agent:
    if agent is None:
        raise HTTPException(503, "Agent not initialized")
    return agent


# ============================================================================
# Routes
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    rag = get_rag_pipeline()
    stats = await rag.get_stats()
    
    return HealthResponse(
        status="healthy",
        vector_db=settings.vector_db_type,
        collection=settings.qdrant_collection,
        documents_count=stats.get("documents_count", 0),
        llm_model=settings.llm_model,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Chat endpoint - main entry point for the widget.
    
    Luồng xử lý:
    1. Optional JWT validation từ Authorization header
    2. Query routing (RAG vs CRM decision)
    3. Execute RAG retrieval + generation
    4. Execute CRM tools nếu cần
    5. Return answer với sources
    6. Log interaction to database (async, non-blocking)
    """
    import asyncio
    
    ag = get_agent()
    
    # Validate auth if token provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        # JWT validation here (implement với PyJWT)
        # For now, just pass through
        logger.info(f"Auth token received for user_id={req.user_id}")
    
    # Map string mode to AgentMode enum
    try:
        mode = AgentMode(req.mode.upper())
    except ValueError:
        mode = AgentMode.HYBRID
    
    # Execute agent
    result = await ag.chat(
        question=req.question,
        user_id=req.user_id,
        email=req.email,
        session_id=req.session_id,
        mode=mode,
    )
    
    # Log interaction to database (non-blocking)
    try:
        asyncio.create_task(_log_chat_async(
            session_id=req.session_id,
            user_id=req.user_id,
            question=req.question,
            answer=result["answer"],
            sources=result.get("sources", []),
            tokens_input=result.get("tokens_input", 0),
            tokens_output=result.get("tokens_output", 0),
            model_used=settings.llm_model,
            mode=req.mode or "HYBRID",
            used_crm=result.get("used_crm", False),
            latency_ms=int(result.get("execution_time_ms", 0)),
        ))
    except Exception as e:
        logger.error(f"Failed to log chat interaction: {e}")
    
    return ChatResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        used_crm=result.get("used_crm", False),
        session_id=req.session_id,
        mode=req.mode,
    )


async def _log_chat_async(
    session_id: str,
    user_id: Optional[str],
    question: str,
    answer: str,
    sources: list,
    tokens_input: int,
    tokens_output: int,
    model_used: str,
    mode: str,
    used_crm: bool,
    latency_ms: int,
) -> None:
    """
    Async helper to log chat interaction to database.
    Non-blocking so it doesn't slow down the response.
    """
    try:
        async with get_db_context() as db:
            await log_chat_interaction(
                db=db,
                session_id=session_id,
                user_id=user_id,
                username=None,
                question=question,
                answer=answer,
                sources=sources,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                model_used=model_used,
                mode=mode,
                used_crm=used_crm,
                latency_ms=latency_ms,
            )
            await db.commit()
            logger.debug(f"Logged chat interaction: session={session_id}")
    except Exception as e:
        logger.error(f"Error logging chat: {e}")


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """
    Ingest documents vào vector database.
    
    Hỗ trợ:
    - Directory path (recursive scan)
    - Single file (DOCX, TXT)
    - Recreate collection option
    """
    import time
    start = time.time()
    
    rag = get_rag_pipeline()
    source_path = Path(req.source)
    
    if not source_path.exists():
        raise HTTPException(400, f"Path not found: {req.source}")
    
    # Recreate collection if requested
    if req.recreate:
        logger.info(f"Recreating collection: {settings.qdrant_collection}")
        await rag.recreate_collection()
    
    # Ingest
    result = await rag.ingest_directory(
        directory=source_path,
        chunk_strategy=req.chunk_strategy or "recursive",
        batch_size=req.batch_size or 32,
    )
    
    elapsed = time.time() - start
    
    return IngestResponse(
        status="success",
        documents_processed=result["documents_processed"],
        chunks_created=result["chunks_created"],
        time_seconds=round(elapsed, 2),
    )


@app.post("/api/ingest/text")
async def ingest_text(
    content: str = Body(..., embed=True),
    source: str = Body("manual"),
    metadata: Optional[dict] = Body(None),
):
    """Ingest a single text snippet directly."""
    rag = get_rag_pipeline()
    
    result = await rag.ingest_documents(
        documents=[{"content": content, "source": source, "metadata": metadata or {}}],
        batch_size=32,
    )
    
    return {"status": "success", "chunks_created": result["chunks_created"]}


@app.delete("/api/ingest/source/{source_name}")
async def delete_by_source(source_name: str):
    """Delete all chunks from a specific source."""
    rag = get_rag_pipeline()
    deleted = await rag.delete_by_source(source_name)
    return {"status": "success", "deleted_count": deleted}


@app.get("/api/stats")
async def stats():
    """Get vector DB statistics."""
    rag = get_rag_pipeline()
    stats_data = await rag.get_stats()
    return stats_data


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
