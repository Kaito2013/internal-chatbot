"""
Middleware - Request logging và Chat interaction logging.
Middleware chạy trước/sau mỗi request.
"""
from datetime import datetime
from typing import Callable, Optional
import json
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .service import log_chat_interaction

logger = logging.getLogger(__name__)


class ChatLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware để log tất cả chat interactions vào database.
    Chỉ áp dụng cho /api/chat endpoint.
    """
    
    def __init__(self, app: ASGIApp, get_db_session):
        """
        Args:
            app: ASGI application
            get_db_session: Callable that returns a database session
        """
        super().__init__(app)
        self.get_db_session = get_db_session
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request và log nếu là chat endpoint."""
        
        # Only log /api/chat POST requests
        if request.url.path == "/api/chat" and request.method == "POST":
            await self._log_chat_request(request)
        
        response = await call_next(request)
        return response
    
    async def _log_chat_request(self, request: Request) -> None:
        """
        Log chat request và response sau khi được xử lý.
        Sử dụng response body để lấy kết quả.
        """
        try:
            # Get request body (already consumed by endpoint)
            body = await request.body()
            request_data = json.loads(body) if body else {}
            
            question = request_data.get("question", "")
            session_id = request_data.get("session_id", "")
            user_id = request_data.get("user_id")
            email = request_data.get("email")
            
            logger.info(f"Chat request: session={session_id}, question={question[:100]}")
            
        except Exception as e:
            logger.error(f"Error logging chat request: {e}")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware để log tất cả requests (timing, status, etc.).
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request và response."""
        import time
        
        start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms:.1f}ms"
        )
        
        return response
