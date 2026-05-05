"""
Conversation Memory - Quản lý context và memory cho agent.
Hỗ trợ short-term (conversation) và long-term (persistent) memory.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import json
import uuid


class MemoryType(Enum):
    """Loại memory."""
    SHORT_TERM = "short_term"     # Trong conversation hiện tại
    LONG_TERM = "long_term"       # Lưu trữ lâu dài (database)
    WORKING = "working"           # Context đang làm việc


@dataclass
class Message:
    """
    Một message trong conversation.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"            # user, assistant, system, tool
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    tool_calls: Optional[List[Dict]] = None  # Lưu tool calls nếu có
    tool_results: Optional[List[Dict]] = None  # Lưu tool results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sang dict."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Tạo Message từ dict."""
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class MemoryConfig:
    """Cấu hình cho memory system."""
    max_short_term_messages: int = 50      # Số messages giữ trong short-term
    max_context_messages: int = 20        # Số messages gửi cho LLM
    max_tokens_estimate: int = 8000       # Ước tính max tokens cho context
    enable_long_term: bool = True          # Có lưu long-term không
    session_ttl_hours: int = 24 * 7       # Session TTL (1 week)
    
    # System prompt
    system_prompt: str = """Bạn là một AI assistant thông minh.
Bạn có thể sử dụng các tools để trả lời câu hỏi của user.
Luôn trả lời bằng tiếng Việt và định dạng rõ ràng."""


@dataclass 
class ConversationContext:
    """
    Context của một conversation session.
    """
    session_id: str
    user_id: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Memory buffers
    short_term_memory: List[Dict[str, Any]] = field(default_factory=list)  # Key facts
    long_term_memory: List[Dict[str, Any]] = field(default_factory=list)    # Persistent info
    
    def add_message(self, role: str, content: str, 
                    tool_calls: Optional[List[Dict]] = None,
                    tool_results: Optional[List[Dict]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Thêm message vào conversation."""
        msg = Message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg
    
    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """Lấy N messages gần nhất."""
        return self.messages[-n:] if self.messages else []
    
    def get_context_for_llm(self, max_messages: int = 20) -> List[Dict[str, Any]]:
        """
        Lấy context để gửi cho LLM.
        Format phù hợp với OpenAI chat format.
        """
        recent = self.get_recent_messages(max_messages)
        
        # Convert sang format cho LLM
        llm_messages = []
        for msg in recent:
            llm_msg = {"role": msg.role, "content": msg.content}
            
            # Add tool_calls nếu có
            if msg.tool_calls:
                llm_msg["tool_calls"] = msg.tool_calls
            
            # Add tool role với tool_call_id
            if msg.role == "tool" and msg.metadata.get("tool_call_id"):
                llm_msg["tool_call_id"] = msg.metadata["tool_call_id"]
            
            llm_messages.append(llm_msg)
        
        return llm_messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session sang dict để lưu trữ."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "short_term_memory": self.short_term_memory,
            "long_term_memory": self.long_term_memory
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Tạo context từ dict."""
        data = data.copy()
        
        # Parse dates
        for dt_field in ["created_at", "updated_at"]:
            if dt_field in data and isinstance(data[dt_field], str):
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        
        # Parse messages
        if "messages" in data:
            data["messages"] = [Message.from_dict(m) for m in data["messages"]]
        
        return cls(**data)


class ConversationMemory:
    """
    Memory system quản lý conversation contexts.
    Hỗ trợ:
    - In-memory storage cho active sessions
    - Serialization để lưu trữ lâu dài
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Khởi tạo Memory.
        
        Args:
            config: Memory configuration
        """
        self.config = config or MemoryConfig()
        
        # In-memory storage
        self._sessions: Dict[str, ConversationContext] = {}
        self._active_session_id: Optional[str] = None
        
        # Long-term storage interface (optional)
        self._storage_backend = None
    
    def create_session(self, session_id: Optional[str] = None, 
                       user_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> ConversationContext:
        """
        Tạo session mới.
        
        Args:
            session_id: ID cho session (auto-generate nếu None)
            user_id: User ID
            metadata: Additional metadata
            
        Returns:
            ConversationContext mới
        """
        session = ConversationContext(
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            metadata=metadata or {}
        )
        
        self._sessions[session.session_id] = session
        self._active_session_id = session.session_id
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Lấy session theo ID."""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str, 
                               user_id: Optional[str] = None) -> ConversationContext:
        """Lấy session hoặc tạo mới nếu không tồn tại."""
        session = self._sessions.get(session_id)
        if not session:
            session = self.create_session(session_id=session_id, user_id=user_id)
        return session
    
    @property
    def active_session(self) -> Optional[ConversationContext]:
        """Lấy session đang active."""
        if self._active_session_id:
            return self._sessions.get(self._active_session_id)
        return None
    
    def set_active_session(self, session_id: str) -> bool:
        """Set active session."""
        if session_id in self._sessions:
            self._active_session_id = session_id
            return True
        return False
    
    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Thêm message vào session.
        
        Args:
            session_id: Session ID
            role: user/assistant/system/tool
            content: Message content
            tool_calls: Tool calls nếu có
            tool_results: Tool results nếu có
            metadata: Additional metadata
            
        Returns:
            Message đã tạo
        """
        session = self.get_or_create_session(session_id)
        return session.add_message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            metadata=metadata or {}
        )
    
    def get_conversation_history(
        self,
        session_id: str,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """
        Lấy conversation history cho session.
        
        Args:
            session_id: Session ID
            max_messages: Giới hạn số messages (lấy messages gần nhất)
            
        Returns:
            List of Messages
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        if max_messages:
            return session.get_recent_messages(max_messages)
        return session.messages
    
    def get_context_for_llm(
        self,
        session_id: str,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Lấy context format phù hợp cho LLM.
        
        Args:
            session_id: Session ID
            max_messages: Giới hạn messages
            
        Returns:
            List of messages format cho LLM
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        max_m = max_messages or self.config.max_context_messages
        return session.get_context_for_llm(max_messages=max_m)
    
    def add_short_term_memory(self, session_id: str, key: str, value: Any) -> None:
        """
        Thêm thông tin vào short-term memory (key facts).
        
        Args:
            session_id: Session ID
            key: Key identifier
            value: Giá trị
        """
        session = self.get_session(session_id)
        if session:
            # Update or add
            found = False
            for item in session.short_term_memory:
                if item.get("key") == key:
                    item["value"] = value
                    item["updated_at"] = datetime.utcnow().isoformat()
                    found = True
                    break
            
            if not found:
                session.short_term_memory.append({
                    "key": key,
                    "value": value,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })
    
    def get_short_term_memory(self, session_id: str) -> List[Dict[str, Any]]:
        """Lấy short-term memory cho session."""
        session = self.get_session(session_id)
        return session.short_term_memory if session else []
    
    def add_long_term_memory(self, session_id: str, memory_type: str, content: Any) -> None:
        """
        Thêm thông tin vào long-term memory.
        
        Args:
            session_id: Session ID
            memory_type: Loại memory (person_info, company_info, etc.)
            content: Nội dung
        """
        session = self.get_session(session_id)
        if session:
            session.long_term_memory.append({
                "type": memory_type,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            })
    
    def search_long_term_memory(
        self, 
        session_id: str, 
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm trong long-term memory.
        
        Args:
            session_id: Session ID
            memory_type: Filter theo type (optional)
            
        Returns:
            List of matching memories
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        memories = session.long_term_memory
        if memory_type:
            memories = [m for m in memories if m.get("type") == memory_type]
        
        return memories
    
    def clear_session(self, session_id: str) -> bool:
        """Xóa session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session_id == session_id:
                self._active_session_id = None
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """Liệt kê tất cả session IDs."""
        return list(self._sessions.keys())
    
    def export_session(self, session_id: str) -> Optional[str]:
        """Export session thành JSON string."""
        session = self.get_session(session_id)
        if session:
            return json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
        return None
    
    def import_session(self, json_str: str) -> Optional[ConversationContext]:
        """Import session từ JSON string."""
        try:
            data = json.loads(json_str)
            session = ConversationContext.from_dict(data)
            self._sessions[session.session_id] = session
            return session
        except Exception:
            return None
    
    def get_session_count(self) -> int:
        """Đếm số lượng sessions."""
        return len(self._sessions)
