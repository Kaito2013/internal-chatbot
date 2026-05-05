"""
SQLAlchemy Models cho Admin Panel.
Chứa: Session, ChatLog, UsageStats, DocumentMetadata.
"""
from datetime import datetime
from typing import Optional, List
import uuid

from sqlalchemy import (
    String, Integer, Boolean, Text, DateTime, Date,
    ForeignKey, JSON, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..db.database import Base


class Session(Base):
    """
    Session model - đại diện cho một cuộc hội thoại.
    Mỗi session có nhiều ChatLog entries.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"sess_{uuid.uuid4().hex[:16]}"
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    messages: Mapped[List["ChatLog"]] = relationship(
        "ChatLog", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, messages={self.message_count})>"


class ChatLog(Base):
    """
    ChatLog model - lưu trữ từng message trong cuộc hội thoại.
    Mỗi user message và assistant response là 1 ChatLog entry.
    """
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' or 'assistant'
    
    # Message content
    question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Sources & context
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    context_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # RAG context
    
    # Token usage tracking
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Metadata
    mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # CHAT, TOOL_USE, REASONING, HYBRID
    used_crm: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Performance
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="messages")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_chat_logs_session_created", "session_id", "created_at"),
        Index("ix_chat_logs_created_at", "created_at"),
        Index("ix_chat_logs_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<ChatLog(id={self.id}, session_id={self.session_id}, role={self.role})>"


class UsageStats(Base):
    """
    UsageStats model - lưu trữ thống kê usage theo ngày.
    Auto-aggregated từ ChatLog records.
    """
    __tablename__ = "usage_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, unique=True, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Token aggregations
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance aggregations
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Integer, default=0)
    
    # Feature usage
    rag_requests: Mapped[int] = mapped_column(Integer, default=0)
    crm_requests: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_usage_stats_date_model", "date", "model"),
    )

    def __repr__(self) -> str:
        return f"<UsageStats(date={self.date}, model={self.model}, requests={self.total_requests})>"


class DocumentMetadata(Base):
    """
    DocumentMetadata model - lưu trữ metadata của documents đã ingest.
    Không lưu content (content nằm trong vector DB).
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # txt, md, pdf, docx, html
    
    # File info
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)  # bytes
    
    # Vector DB info
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Processing info
    chunk_strategy: Mapped[str] = mapped_column(String(32), default="recursive")
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Document(source={self.source}, chunks={self.chunk_count})>"


class AdminUser(Base):
    """
    AdminUser model - user cho admin panel authentication.
    """
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    
    # Permissions
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    can_upload: Mapped[bool] = mapped_column(Boolean, default=True)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_stats: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<AdminUser(username={self.username}, is_superadmin={self.is_superadmin})>"
