"""
Admin API Routes - REST endpoints cho Admin Panel.
Bao gồm: Auth, Documents, Sessions, Statistics.
"""
import os
import uuid
import json
import time
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Header
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_db
from ..config import settings
from .schemas import (
    AdminLoginRequest, AdminLoginResponse, AdminUserResponse,
    DocumentUploadResponse, DocumentListResponse, DocumentChunksResponse, DocumentChunkPreview,
    SessionListResponse, SessionResponse, SessionDetailResponse, ChatLogResponse,
    SessionSearchResponse, ChatExportResponse,
    OverviewStats, TokenUsageResponse, RAGEffectivenessResponse, TopSourcesResponse,
)
from .service import (
    get_sessions, get_session_by_id, delete_session, search_sessions,
    get_documents, get_document_by_source, create_document_metadata,
    update_document_chunks, delete_document,
    get_overview_stats, get_token_usage, get_rag_effectiveness, get_top_sources,
    get_admin_by_username, update_last_login, ensure_default_admin,
    serialize_session, serialize_document,
)
from ..rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/admin", tags=["admin"])


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_admin_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Dependency để verify admin JWT token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        import jwt
        from .service import get_admin_by_username
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.admin_secret_key,
            algorithms=["HS256"],
        )
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        user = await get_admin_by_username(db, username)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        return {
            "id": user.id,
            "username": user.username,
            "is_superadmin": user.is_superadmin,
            "can_upload": user.can_upload,
            "can_delete": user.can_delete,
            "can_view_stats": user.can_view_stats,
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def create_access_token(username: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    import jwt
    from datetime import datetime, timezone
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.admin_token_expire_hours)
    
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(payload, settings.admin_secret_key, algorithm="HS256")


# =============================================================================
# Auth Endpoints
# =============================================================================

@router.post("/auth/login", response_model=AdminLoginResponse)
async def login(
    req: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login với username/password, trả về JWT token."""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Get user
    user = await get_admin_by_username(db, req.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    # Update last login
    await update_last_login(db, user.id)
    await db.commit()
    
    # Create token
    access_token = create_access_token(user.username)
    
    return AdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.admin_token_expire_hours * 3600,
        user=AdminUserResponse(
            id=user.id,
            username=user.username,
            is_superadmin=user.is_superadmin,
            can_upload=user.can_upload,
            can_delete=user.can_delete,
            can_view_stats=user.can_view_stats,
            created_at=user.created_at,
            last_login=user.last_login,
            is_active=user.is_active,
        )
    )


@router.post("/auth/verify")
async def verify_token(
    current_user: dict = Depends(get_current_admin_user),
):
    """Verify current token."""
    return {"valid": True, "user": current_user}


# =============================================================================
# Document Endpoints
# =============================================================================

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents."""
    documents, total = await get_documents(db, page, page_size, is_active)
    
    total_pages = (total + page_size - 1) // page_size
    
    return DocumentListResponse(
        documents=[serialize_document(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    chunk_strategy: str = Form("recursive"),
    recreate: bool = Form(False),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload và ingest document.
    Supported formats: txt, md, pdf, docx, html
    """
    if not current_user.get("can_upload"):
        raise HTTPException(status_code=403, detail="Not authorized to upload")
    
    # Validate file extension
    allowed = settings.allowed_extensions.split(",")
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset position
    
    max_size = settings.max_file_size_mb * 1024 * 1024
    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
        )
    
    # Create upload directory
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_id = str(uuid.uuid4())[:8]
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    content = await file.read()
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse content based on file type
    text_content = await parse_document(file_path, ext)
    
    # Ingest to vector DB
    from ..main import rag_pipeline  # Access global RAG pipeline
    from ..agentic.agent import Agent  # For import
    
    if recreate:
        await rag_pipeline.recreate_collection()
    
    start_time = time.time()
    
    result = await rag_pipeline.ingest_documents(
        documents=[{
            "content": text_content,
            "source": file_path,
            "metadata": {"filename": file.filename, "file_type": ext}
        }],
        batch_size=32,
    )
    
    processing_time = (time.time() - start_time) * 1000
    
    # Create metadata record
    doc = await create_document_metadata(
        db=db,
        source=file_path,
        filename=file.filename,
        file_type=ext,
        file_size=size,
        chunk_count=result.get("total_chunks", 0),
        processing_time_ms=processing_time,
        chunk_strategy=chunk_strategy,
    )
    
    await db.commit()
    
    return DocumentUploadResponse(
        id=doc.id,
        source=file_path,
        filename=file.filename,
        file_type=ext,
        file_size=size,
        chunk_count=result.get("total_chunks", 0),
        processing_time_ms=processing_time,
        status="success",
    )


@router.delete("/documents/{source:path}")
async def remove_document(
    source: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete document (soft delete)."""
    if not current_user.get("can_delete"):
        raise HTTPException(status_code=403, detail="Not authorized to delete")
    
    from ..main import rag_pipeline
    
    success = await delete_document(
        db=db,
        source=source,
        delete_from_vector_db=True,
        rag_pipeline=rag_pipeline,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.commit()
    
    return {"status": "success", "message": f"Document '{source}' deleted"}


@router.post("/documents/{source:path}/reingest")
async def reingest_document(
    source: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-ingest a document (after editing)."""
    if not current_user.get("can_upload"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get document metadata
    doc = await get_document_by_source(db, source)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Read file content
    if not os.path.exists(source):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    ext = doc.file_type
    text_content = await parse_document(source, ext)
    
    # Re-ingest
    from ..main import rag_pipeline
    
    start_time = time.time()
    result = await rag_pipeline.ingest_documents(
        documents=[{
            "content": text_content,
            "source": source,
            "metadata": {"filename": doc.filename, "file_type": ext}
        }],
        batch_size=32,
    )
    
    processing_time = (time.time() - start_time) * 1000
    
    # Update metadata
    await update_document_chunks(
        db=db,
        source=source,
        chunk_count=result.get("total_chunks", 0),
        processing_time_ms=int(processing_time),
    )
    
    await db.commit()
    
    return {
        "status": "success",
        "chunk_count": result.get("total_chunks", 0),
        "processing_time_ms": processing_time,
    }


# =============================================================================
# Session / Chat Log Endpoints
# =============================================================================

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions."""
    sessions, total = await get_sessions(db, page, page_size, user_id)
    
    total_pages = (total + page_size - 1) // page_size
    
    return SessionListResponse(
        sessions=[serialize_session(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/search", response_model=SessionSearchResponse)
async def search_chat_sessions(
    q: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Search sessions by content."""
    sessions = await search_sessions(db, q, limit)
    
    return SessionSearchResponse(
        sessions=[serialize_session(s) for s in sessions],
        total=len(sessions),
        query=q,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get session detail with messages."""
    session = await get_session_by_id(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionDetailResponse(
        id=session.id,
        user_id=session.user_id,
        username=session.username,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=session.message_count,
        is_active=session.is_active,
        messages=[
            ChatLogResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                question=m.question,
                answer=m.answer,
                sources_json=m.sources_json,
                tokens_input=m.tokens_input,
                tokens_output=m.tokens_output,
                model_used=m.model_used,
                mode=m.mode,
                used_crm=m.used_crm,
                latency_ms=m.latency_ms,
                created_at=m.created_at,
            )
            for m in sorted(session.messages, key=lambda x: x.created_at)
        ],
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session."""
    if not current_user.get("can_delete"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await delete_session(db, session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.commit()
    
    return {"status": "success", "message": f"Session '{session_id}' deleted"}


@router.get("/sessions/export/{session_id}")
async def export_session(
    session_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Export session as JSON or CSV."""
    session = await get_session_by_id(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if format == "json":
        content = json.dumps({
            "session_id": session.id,
            "user_id": session.user_id,
            "username": session.username,
            "created_at": session.created_at.isoformat(),
            "messages": [
                {
                    "role": m.role,
                    "question": m.question,
                    "answer": m.answer,
                    "tokens_input": m.tokens_input,
                    "tokens_output": m.tokens_output,
                    "created_at": m.created_at.isoformat(),
                }
                for m in sorted(session.messages, key=lambda x: x.created_at)
            ]
        }, ensure_ascii=False, indent=2)
        
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.json"}
        )
    
    else:  # csv
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["role", "question", "answer", "tokens_input", "tokens_output", "created_at"])
        
        for m in sorted(session.messages, key=lambda x: x.created_at):
            writer.writerow([
                m.role,
                m.question or "",
                m.answer or "",
                m.tokens_input or 0,
                m.tokens_output or 0,
                m.created_at.isoformat(),
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"}
        )


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/stats/overview", response_model=OverviewStats)
async def get_stats_overview(
    period: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get overview statistics."""
    return await get_overview_stats(db, period)


@router.get("/stats/tokens", response_model=TokenUsageResponse)
async def get_token_stats(
    period: str = Query("7d", regex="^(7d|30d|90d)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get token usage over time."""
    return await get_token_usage(db, period)


@router.get("/stats/rag-effectiveness", response_model=RAGEffectivenessResponse)
async def get_rag_stats(
    period: str = Query("7d", regex="^(7d|30d|90d)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get RAG effectiveness metrics."""
    return await get_rag_effectiveness(db, period)


@router.get("/stats/top-sources", response_model=TopSourcesResponse)
async def get_stats_top_sources(
    period: str = Query("7d", regex="^(7d|30d|90d)$"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get most referenced document sources."""
    return await get_top_sources(db, period, limit)


# =============================================================================
# Helper Functions
# =============================================================================

async def parse_document(file_path: str, file_type: str) -> str:
    """
    Parse document content based on file type.
    Returns text content.
    """
    if file_type == "txt" or file_type == "md":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    
    elif file_type == "pdf":
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")
    
    elif file_type == "docx":
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to parse DOCX: {e}")
    
    elif file_type == "html":
        try:
            from bs4 import BeautifulSoup
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator="\n\n", strip=True)
            return text
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to parse HTML: {e}")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")
