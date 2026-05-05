"""
Admin Service - Business logic cho Admin Panel.
Xử lý database operations cho sessions, logs, documents, và stats.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
import json
import uuid

from sqlalchemy import select, func, desc, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from ..db.database import async_session_factory
from .models import Session, ChatLog, UsageStats, DocumentMetadata, AdminUser
from .schemas import (
    DocumentUploadResponse, DocumentResponse, DocumentListResponse,
    SessionResponse, SessionDetailResponse, SessionListResponse,
    OverviewStats, TokenStats, LatencyStats,
    TokenUsageResponse, TokenUsageDataPoint,
    RAGEffectivenessResponse, RAGEffectivenessDataPoint,
    TopSourcesResponse, TopSource, AdminLoginResponse, AdminUserResponse,
)
from ..config import settings
from ..rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)


# =============================================================================
# Session & ChatLog Services
# =============================================================================

async def get_or_create_session(
    db: AsyncSession,
    session_id: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None
) -> Session:
    """
    Get existing session hoặc create new one.
    """
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        session = Session(
            id=session_id,
            user_id=user_id,
            username=username,
        )
        db.add(session)
        await db.flush()
    
    return session


async def log_chat_interaction(
    db: AsyncSession,
    session_id: str,
    user_id: Optional[str],
    username: Optional[str],
    question: str,
    answer: str,
    sources: List[Dict[str, Any]],
    tokens_input: int,
    tokens_output: int,
    model_used: str,
    mode: str,
    used_crm: bool,
    latency_ms: int,
) -> ChatLog:
    """
    Log một chat interaction vào database.
    Tự động tạo session nếu chưa có.
    """
    # Get or create session
    session = await get_or_create_session(db, session_id, user_id, username)
    
    # Update session message count
    session.message_count += 1
    session.updated_at = datetime.utcnow()
    
    # Create chat log
    chat_log = ChatLog(
        session_id=session_id,
        role="user",
        question=question,
        answer=answer,
        sources_json=json.dumps(sources, ensure_ascii=False) if sources else None,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        model_used=model_used,
        mode=mode,
        used_crm=used_crm,
        latency_ms=latency_ms,
    )
    db.add(chat_log)
    
    # Update usage stats
    await update_usage_stats(
        db=db,
        date=datetime.utcnow().date(),
        model=model_used,
        input_tokens=tokens_input,
        output_tokens=tokens_output,
        latency_ms=latency_ms,
        rag_request=len(sources) > 0,
        crm_request=used_crm,
    )
    
    await db.flush()
    return chat_log


async def get_sessions(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[Session], int]:
    """
    Get paginated list of sessions.
    """
    query = select(Session)
    count_query = select(func.count(Session.id))
    
    if user_id:
        query = query.where(Session.user_id == user_id)
        count_query = count_query.where(Session.user_id == user_id)
    
    if search:
        search_filter = or_(
            Session.id.ilike(f"%{search}%"),
            Session.username.ilike(f"%{search}%"),
            Session.user_id.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(desc(Session.updated_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return list(sessions), total


async def get_session_by_id(
    db: AsyncSession,
    session_id: str,
) -> Optional[Session]:
    """
    Get session by ID với messages.
    """
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.messages))
        .where(Session.id == session_id)
    )
    return result.scalar_one_or_none()


async def delete_session(
    db: AsyncSession,
    session_id: str,
) -> bool:
    """
    Delete a session và tất cả messages.
    """
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return False
    
    await db.delete(session)
    await db.flush()
    return True


async def search_sessions(
    db: AsyncSession,
    query_text: str,
    limit: int = 50,
) -> List[Session]:
    """
    Search sessions by content (questions/answers).
    """
    # Search in chat_logs
    subquery = select(ChatLog.session_id).where(
        or_(
            ChatLog.question.ilike(f"%{query_text}%"),
            ChatLog.answer.ilike(f"%{query_text}%"),
        )
    ).distinct()
    
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.messages))
        .where(Session.id.in_(subquery))
        .order_by(desc(Session.updated_at))
        .limit(limit)
    )
    
    return list(result.scalars().all())


# =============================================================================
# Usage Stats Services
# =============================================================================

async def update_usage_stats(
    db: AsyncSession,
    date: date,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    rag_request: bool = False,
    crm_request: bool = False,
) -> None:
    """
    Update or create daily usage stats.
    Uses upsert pattern.
    """
    # Check if stats exist for this date
    result = await db.execute(
        select(UsageStats).where(
            and_(
                UsageStats.date == date,
                UsageStats.model == model,
            )
        )
    )
    stats = result.scalar_one_or_none()
    
    if stats:
        # Update existing
        stats.total_requests += 1
        stats.total_input_tokens += input_tokens
        stats.total_output_tokens += output_tokens
        stats.total_latency_ms += latency_ms
        stats.avg_latency_ms = stats.total_latency_ms / stats.total_requests
        if rag_request:
            stats.rag_requests += 1
        if crm_request:
            stats.crm_requests += 1
    else:
        # Create new
        stats = UsageStats(
            date=date,
            model=model,
            total_requests=1,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            total_latency_ms=latency_ms,
            avg_latency_ms=latency_ms,
            rag_requests=1 if rag_request else 0,
            crm_requests=1 if crm_request else 0,
        )
        db.add(stats)
    
    await db.flush()


async def get_overview_stats(
    db: AsyncSession,
    period_days: int = 30,
) -> OverviewStats:
    """
    Get overview statistics for dashboard.
    """
    start_date = datetime.utcnow().date() - timedelta(days=period_days)
    
    # Total sessions
    sessions_result = await db.execute(
        select(func.count(Session.id)).where(
            Session.created_at >= start_date
        )
    )
    total_sessions = sessions_result.scalar() or 0
    
    # Total messages
    messages_result = await db.execute(
        select(func.count(ChatLog.id)).where(
            ChatLog.created_at >= start_date
        )
    )
    total_messages = messages_result.scalar() or 0
    
    # Total unique users
    users_result = await db.execute(
        select(func.count(func.distinct(Session.user_id))).where(
            and_(
                Session.user_id.isnot(None),
                Session.created_at >= start_date,
            )
        )
    )
    total_users = users_result.scalar() or 0
    
    # Total documents
    docs_result = await db.execute(
        select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.is_active == True
        )
    )
    total_documents = docs_result.scalar() or 0
    
    # Total chunks
    chunks_result = await db.execute(
        select(func.sum(DocumentMetadata.chunk_count)).where(
            DocumentMetadata.is_active == True
        )
    )
    total_chunks = chunks_result.scalar() or 0
    
    # Token stats
    token_result = await db.execute(
        select(
            func.sum(ChatLog.tokens_input),
            func.sum(ChatLog.tokens_output),
            func.avg(ChatLog.latency_ms),
        ).where(
            ChatLog.created_at >= start_date
        )
    )
    token_row = token_result.tuple()
    total_input = token_row[0] or 0
    total_output = token_row[1] or 0
    avg_latency = token_row[2] or 0
    
    # Calculate averages
    avg_input = total_input / total_messages if total_messages > 0 else 0
    avg_output = total_output / total_messages if total_messages > 0 else 0
    
    token_stats = TokenStats(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_input + total_output,
        avg_input_tokens=round(avg_input, 1),
        avg_output_tokens=round(avg_output, 1),
    )
    
    return OverviewStats(
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_users=total_users,
        total_documents=total_documents,
        total_chunks=total_chunks,
        avg_latency_ms=round(avg_latency, 1),
        token_stats=token_stats,
        period_days=period_days,
    )


async def get_token_usage(
    db: AsyncSession,
    period: str = "7d",
) -> TokenUsageResponse:
    """
    Get token usage data for charts.
    period: 7d, 30d, 90d
    """
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    result = await db.execute(
        select(
            UsageStats.date,
            func.sum(UsageStats.total_input_tokens),
            func.sum(UsageStats.total_output_tokens),
            func.sum(UsageStats.total_requests),
        )
        .where(UsageStats.date >= start_date)
        .group_by(UsageStats.date)
        .order_by(UsageStats.date)
    )
    
    data = []
    total_input = 0
    total_output = 0
    total_requests = 0
    
    for row in result.all():
        data.append(TokenUsageDataPoint(
            date=row[0],
            input_tokens=row[1] or 0,
            output_tokens=row[2] or 0,
            total_tokens=(row[1] or 0) + (row[2] or 0),
            request_count=row[3] or 0,
        ))
        total_input += row[1] or 0
        total_output += row[2] or 0
        total_requests += row[3] or 0
    
    return TokenUsageResponse(
        period=period,
        data=data,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_requests=total_requests,
    )


async def get_rag_effectiveness(
    db: AsyncSession,
    period: str = "7d",
) -> RAGEffectivenessResponse:
    """
    Get RAG effectiveness data.
    """
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    result = await db.execute(
        select(
            UsageStats.date,
            func.sum(UsageStats.rag_requests),
            func.sum(UsageStats.total_requests),
        )
        .where(UsageStats.date >= start_date)
        .group_by(UsageStats.date)
        .order_by(UsageStats.date)
    )
    
    data = []
    total_rag = 0
    total_requests = 0
    
    for row in result.all():
        rag = row[1] or 0
        total_req = row[2] or 0
        rate = rag / total_req if total_req > 0 else 0
        
        data.append(RAGEffectivenessDataPoint(
            date=row[0],
            rag_requests=rag,
            total_requests=total_req,
            effectiveness_rate=round(rate, 3),
        ))
        total_rag += rag
        total_requests += total_req
    
    overall_rate = total_rag / total_requests if total_requests > 0 else 0
    
    return RAGEffectivenessResponse(
        period=period,
        data=data,
        overall_effectiveness_rate=round(overall_rate, 3),
        total_rag_requests=total_rag,
        total_requests=total_requests,
    )


async def get_top_sources(
    db: AsyncSession,
    period: str = "7d",
    limit: int = 10,
) -> TopSourcesResponse:
    """
    Get most referenced document sources.
    """
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 7)
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    # Parse sources from chat_logs
    result = await db.execute(
        select(
            ChatLog.sources_json,
            func.max(ChatLog.created_at),
        )
        .where(ChatLog.created_at >= start_date)
        .group_by(ChatLog.sources_json)
    )
    
    source_counts: Dict[str, Dict] = {}
    
    for row in result.all():
        sources_json = row[0]
        last_used = row[1]
        
        if not sources_json:
            continue
        
        try:
            sources = json.loads(sources_json)
            if not isinstance(sources, list):
                sources = [sources]
            
            for source in sources:
                source_name = source.get("source", "unknown")
                if source_name not in source_counts:
                    source_counts[source_name] = {
                        "count": 0,
                        "last_used": last_used,
                    }
                source_counts[source_name]["count"] += 1
                if last_used > source_counts[source_name]["last_used"]:
                    source_counts[source_name]["last_used"] = last_used
        except json.JSONDecodeError:
            continue
    
    # Sort by count and take top N
    sorted_sources = sorted(
        source_counts.items(),
        key=lambda x: x[1]["count"],
        reverse=True,
    )[:limit]
    
    # Get document metadata
    top_sources = []
    for source_name, stats in sorted_sources:
        doc_result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.source == source_name)
        )
        doc = doc_result.scalar_one_or_none()
        
        top_sources.append(TopSource(
            source=source_name,
            filename=doc.filename if doc else source_name.split("/")[-1],
            reference_count=stats["count"],
            last_referenced=stats["last_used"],
        ))
    
    return TopSourcesResponse(
        sources=top_sources,
        period=period,
    )


# =============================================================================
# Document Services
# =============================================================================

async def create_document_metadata(
    db: AsyncSession,
    source: str,
    filename: str,
    file_type: str,
    file_size: int,
    chunk_count: int,
    processing_time_ms: float,
    chunk_strategy: str = "recursive",
) -> DocumentMetadata:
    """
    Create document metadata record.
    """
    doc = DocumentMetadata(
        source=source,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        chunk_count=chunk_count,
        chunk_strategy=chunk_strategy,
        processing_time_ms=int(processing_time_ms),
    )
    db.add(doc)
    await db.flush()
    return doc


async def get_documents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    is_active: Optional[bool] = None,
) -> Tuple[List[DocumentMetadata], int]:
    """
    Get paginated list of documents.
    """
    query = select(DocumentMetadata)
    count_query = select(func.count(DocumentMetadata.id))
    
    if is_active is not None:
        query = query.where(DocumentMetadata.is_active == is_active)
        count_query = count_query.where(DocumentMetadata.is_active == is_active)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(desc(DocumentMetadata.uploaded_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return list(documents), total


async def get_document_by_source(
    db: AsyncSession,
    source: str,
) -> Optional[DocumentMetadata]:
    """
    Get document by source path.
    """
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.source == source)
    )
    return result.scalar_one_or_none()


async def update_document_chunks(
    db: AsyncSession,
    source: str,
    chunk_count: int,
    processing_time_ms: int,
) -> Optional[DocumentMetadata]:
    """
    Update document chunk count after re-ingestion.
    """
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.source == source)
    )
    doc = result.scalar_one_or_none()
    
    if doc:
        doc.chunk_count = chunk_count
        doc.processing_time_ms = processing_time_ms
        doc.last_ingested_at = datetime.utcnow()
        await db.flush()
    
    return doc


async def delete_document(
    db: AsyncSession,
    source: str,
    delete_from_vector_db: bool = True,
    rag_pipeline: Optional[RAGPipeline] = None,
) -> bool:
    """
    Soft delete document (set is_active=False).
    Optionally also delete from vector DB.
    """
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.source == source)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        return False
    
    # Soft delete
    doc.is_active = False
    await db.flush()
    
    # Optionally delete from vector DB
    if delete_from_vector_db and rag_pipeline:
        try:
            await rag_pipeline.delete_by_source(source)
        except Exception as e:
            logger.error(f"Failed to delete from vector DB: {e}")
    
    return True


# =============================================================================
# Admin Auth Services
# =============================================================================

async def get_admin_by_username(
    db: AsyncSession,
    username: str,
) -> Optional[AdminUser]:
    """
    Get admin user by username.
    """
    result = await db.execute(
        select(AdminUser).where(
            and_(
                AdminUser.username == username,
                AdminUser.is_active == True,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_admin_user(
    db: AsyncSession,
    username: str,
    password_hash: str,
    is_superadmin: bool = False,
    can_upload: bool = True,
    can_delete: bool = True,
    can_view_stats: bool = True,
) -> AdminUser:
    """
    Create new admin user.
    """
    user = AdminUser(
        username=username,
        password_hash=password_hash,
        is_superadmin=is_superadmin,
        can_upload=can_upload,
        can_delete=can_delete,
        can_view_stats=can_view_stats,
    )
    db.add(user)
    await db.flush()
    return user


async def update_last_login(
    db: AsyncSession,
    user_id: int,
) -> None:
    """
    Update last login timestamp.
    """
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.last_login = datetime.utcnow()
        await db.flush()


async def ensure_default_admin(
    db: AsyncSession,
) -> Tuple[AdminUser, bool]:
    """
    Ensure default admin user exists.
    Returns (user, created) tuple.
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    admin = await get_admin_by_username(db, settings.admin_username)
    
    if admin:
        return admin, False
    
    # Create default admin
    password_hash = pwd_context.hash(settings.admin_password)
    admin = await create_admin_user(
        db=db,
        username=settings.admin_username,
        password_hash=password_hash,
        is_superadmin=True,
    )
    
    return admin, True


# =============================================================================
# Helper Functions
# =============================================================================

def serialize_session(session: Session) -> SessionResponse:
    """
    Convert Session model to SessionResponse.
    """
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        username=session.username,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=session.message_count,
        is_active=session.is_active,
    )


def serialize_document(doc: DocumentMetadata) -> DocumentResponse:
    """
    Convert DocumentMetadata to DocumentResponse.
    """
    return DocumentResponse(
        id=doc.id,
        source=doc.source,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        chunk_strategy=doc.chunk_strategy,
        processing_time_ms=doc.processing_time_ms,
        uploaded_at=doc.uploaded_at,
        last_ingested_at=doc.last_ingested_at,
        is_active=doc.is_active,
    )
