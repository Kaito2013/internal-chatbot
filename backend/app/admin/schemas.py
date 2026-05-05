"""
Pydantic Schemas cho Admin Panel API.
Validation và serialization cho request/response.
"""
from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Document Schemas
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """Response sau khi upload document thành công."""
    id: int
    source: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    processing_time_ms: float
    status: str


class DocumentResponse(BaseModel):
    """Document metadata response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    filename: str
    file_type: str
    file_size: Optional[int] = None
    chunk_count: int
    chunk_strategy: str
    processing_time_ms: Optional[int] = None
    uploaded_at: datetime
    last_ingested_at: datetime
    is_active: bool


class DocumentListResponse(BaseModel):
    """Response cho document list API."""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentChunkPreview(BaseModel):
    """Preview một chunk của document."""
    chunk_id: str
    content: str
    char_count: int
    word_count: int
    score: Optional[float] = None  # Relevance score nếu có search


class DocumentChunksResponse(BaseModel):
    """Response cho document chunk preview."""
    source: str
    total_chunks: int
    chunks: List[DocumentChunkPreview]


# =============================================================================
# Session & Chat Log Schemas
# =============================================================================

class ChatLogResponse(BaseModel):
    """Một message trong chat session."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    role: str
    question: Optional[str] = None
    answer: Optional[str] = None
    sources_json: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    model_used: Optional[str] = None
    mode: Optional[str] = None
    used_crm: bool
    latency_ms: Optional[int] = None
    created_at: datetime


class SessionResponse(BaseModel):
    """Session metadata response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_active: bool


class SessionDetailResponse(BaseModel):
    """Session với messages chi tiết."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_active: bool
    messages: List[ChatLogResponse]


class SessionListResponse(BaseModel):
    """Response cho session list API."""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int


class SessionSearchResponse(BaseModel):
    """Response cho session search API."""
    sessions: List[SessionResponse]
    total: int
    query: str


class ChatExportResponse(BaseModel):
    """Response cho export functionality."""
    filename: str
    content: str
    content_type: str


# =============================================================================
# Statistics Schemas
# =============================================================================

class TokenStats(BaseModel):
    """Token usage statistics."""
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_input_tokens: float
    avg_output_tokens: float


class LatencyStats(BaseModel):
    """Latency statistics."""
    avg_latency_ms: float
    min_latency_ms: int
    max_latency_ms: int
    p95_latency_ms: int


class OverviewStats(BaseModel):
    """Overview statistics response."""
    total_sessions: int
    total_messages: int
    total_users: int
    total_documents: int
    total_chunks: int
    avg_latency_ms: float
    token_stats: TokenStats
    period_days: int


class TokenUsageDataPoint(BaseModel):
    """Một data point cho token usage chart."""
    date: date
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_count: int


class TokenUsageResponse(BaseModel):
    """Response cho token usage API."""
    period: str  # 7d, 30d, 90d
    data: List[TokenUsageDataPoint]
    total_input_tokens: int
    total_output_tokens: int
    total_requests: int


class RAGEffectivenessDataPoint(BaseModel):
    """Một data point cho RAG effectiveness chart."""
    date: date
    rag_requests: int
    total_requests: int
    effectiveness_rate: float


class RAGEffectivenessResponse(BaseModel):
    """Response cho RAG effectiveness API."""
    period: str
    data: List[RAGEffectivenessDataPoint]
    overall_effectiveness_rate: float
    total_rag_requests: int
    total_requests: int


class TopSource(BaseModel):
    """Document source được reference nhiều nhất."""
    source: str
    filename: str
    reference_count: int
    last_referenced: Optional[datetime] = None


class TopSourcesResponse(BaseModel):
    """Response cho top sources API."""
    sources: List[TopSource]
    period: str


class ChartDataPoint(BaseModel):
    """Generic chart data point."""
    label: str
    value: float
    secondary_value: Optional[float] = None


class DailyStatsResponse(BaseModel):
    """Response cho daily stats chart."""
    period: str
    labels: List[str]
    datasets: List[dict]  # Flexible datasets for Chart.js


# =============================================================================
# Admin Auth Schemas
# =============================================================================

class AdminLoginRequest(BaseModel):
    """Admin login request."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)


class AdminLoginResponse(BaseModel):
    """Admin login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "AdminUserResponse"


class AdminUserResponse(BaseModel):
    """Admin user info (không include password)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_superadmin: bool
    can_upload: bool
    can_delete: bool
    can_view_stats: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool


class AdminUserCreate(BaseModel):
    """Schema để tạo admin user mới."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)
    is_superadmin: bool = False
    can_upload: bool = True
    can_delete: bool = True
    can_view_stats: bool = True


# Update forward reference
AdminLoginResponse.model_rebuild()
