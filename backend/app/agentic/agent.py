"""
Agent Core - Main Agent implementation.
Xử lý orchestration giữa LLM, tools và memory.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
import json
import time
import asyncio
from datetime import datetime

from .memory import ConversationMemory, MemoryConfig, ConversationContext
from .tools import ToolRegistry, ToolResult, ToolCategory


class AgentMode(Enum):
    """Chế độ hoạt động của agent."""
    CHAT = "chat"                 # Conversational
    TOOL_USE = "tool_use"        # Sử dụng tools
    REASONING = "reasoning"       # Step-by-step reasoning
    HYBRID = "hybrid"             # Kết hợp tất cả


class ReasoningStrategy(Enum):
    """Chiến lược reasoning."""
    ZERO_SHOT = "zero_shot"       # Không có example
    FEW_SHOT = "few_shot"         # Với examples
    CHAIN_OF_THOUGHT = "cot"      # Chain of thought
    TREE_OF_THOUGHT = "tot"       # Tree of thought


@dataclass
class AgentConfig:
    """Cấu hình cho Agent."""
    # Model settings
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000
    api_base: Optional[str] = None  # Custom API base (for LiteLLM)
    
    # Behavior settings
    mode: AgentMode = AgentMode.HYBRID
    reasoning_strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    
    # Tool settings
    max_tool_calls: int = 5
    tool_call_timeout: float = 30.0
    
    # Memory settings
    memory_config: Optional[MemoryConfig] = None
    
    # System prompt
    system_prompt: str = """Bạn là một AI Assistant thông minh cho hệ thống nội bộ.
Bạn có thể sử dụng các tools để trả lời câu hỏi và thực hiện tác vụ.
Hãy trả lời bằng tiếng Việt một cách rõ ràng và hữu ích.

Khi được yêu cầu tính toán, hãy sử dụng tool calculate hoặc crm_calculate.
Khi cần tìm thông tin, hãy sử dụng tool search_knowledge."""

    # Reasoning prompt (for chain of thought)
    reasoning_prompt: str = """
Hãy suy nghĩ từng bước:
1. Hiểu câu hỏi của user
2. Xác định thông tin cần thiết
3. Lên kế hoạch sử dụng tools (nếu cần)
4. Thực hiện và tổng hợp kết quả
5. Đưa ra câu trả lời cuối cùng"""


@dataclass
class AgentResponse:
    """Response từ agent."""
    content: str                          # Nội dung câu trả lời
    session_id: str                       # Session ID
    tool_calls: List[Dict[str, Any]]      # Các tool đã gọi
    tool_results: List[ToolResult]       # Kết quả từ tools
    reasoning_steps: List[str]            # Các bước reasoning
    sources: List[Dict[str, Any]]         # Sources tham khảo
    metadata: Dict[str, Any]              # Metadata bổ sung
    success: bool = True
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sang dict."""
        return {
            "content": self.content,
            "session_id": self.session_id,
            "tool_calls": self.tool_calls,
            "tool_results": [r.to_dict() for r in self.tool_results],
            "reasoning_steps": self.reasoning_steps,
            "sources": self.sources,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms
        }


class Agent:
    """
    Main Agent class.
    Xử lý orchestration giữa:
    - LLM (OpenAI/LiteLLM)
    - Tools (RAG, Calculator, CRM, etc.)
    - Memory (Conversation context)
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory: Optional[ConversationMemory] = None,
        llm_client: Optional[Any] = None,
        llm_model: Optional[str] = None,
        llm_temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Khởi tạo Agent.
        
        Args:
            config: Agent configuration
            tool_registry: Registry chứa các tools
            memory: Conversation memory
            llm_client: OpenAI-compatible async LLM client
            llm_model: Model name (e.g. "gpt-4o-mini", "MiniMax-Text-01")
            llm_temperature: Sampling temperature
            max_tokens: Max output tokens
        """
        # Merge config with direct params (direct params take precedence)
        if config is None:
            config = AgentConfig()
        
        if llm_model is not None:
            config.model = llm_model
        if llm_temperature is not None:
            config.temperature = llm_temperature
        if max_tokens is not None:
            config.max_tokens = max_tokens
        
        self.config = config
        self.tool_registry = tool_registry or ToolRegistry()
        self.memory = memory or ConversationMemory(self.config.memory_config)
        
        # LLM Client
        self._llm_client = llm_client
        self._use_mock_llm = llm_client is None
        
        if not self._use_mock_llm:
            self._setup_llm_client()
    
    def _setup_llm_client(self) -> None:
        """Setup LLM client (OpenAI or LiteLLM compatible)."""
        if self._llm_client is None:
            api_key = self.config.api_base or "sk-dummy"
            
            try:
                from openai import AsyncOpenAI
                
                # Check nếu dùng LiteLLM proxy
                if self.config.api_base:
                    self._llm_client = AsyncOpenAI(
                        api_key=api_key,
                        base_url=self.config.api_base
                    )
                else:
                    self._llm_client = AsyncOpenAI(api_key=api_key)
                    
            except ImportError:
                self._use_mock_llm = True
    
    async def process(
        self,
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None,
        stream: bool = False
    ) -> AgentResponse:
        """
        Xử lý user input và trả về response.
        
        Args:
            user_input: Câu hỏi/tasks từ user
            session_id: Session ID để tracking
            user_id: User ID (optional)
            stream: Enable streaming response
            
        Returns:
            AgentResponse
        """
        start_time = time.perf_counter()
        
        # Ensure session exists
        session = self.memory.get_or_create_session(session_id, user_id)
        
        # Add user message to memory
        self.memory.add_message_to_session(
            session_id=session_id,
            role="user",
            content=user_input
        )
        
        # Initialize response tracking
        tool_calls_made: List[Dict[str, Any]] = []
        tool_results: List[ToolResult] = []
        reasoning_steps: List[str] = []
        sources: List[Dict[str, Any]] = []
        
        try:
            # === REASONING PHASE ===
            if self.config.mode in [AgentMode.REASONING, AgentMode.HYBRID]:
                reasoning_steps.append(f"Input: {user_input}")
            
            # === TOOL CALLING PHASE ===
            if self.config.mode in [AgentMode.TOOL_USE, AgentMode.HYBRID]:
                # Get available tools definition for LLM
                available_tools = self.tool_registry.get_all_definitions()
                
                # Build messages for LLM
                messages = self._build_messages(
                    session_id=session_id,
                    reasoning=self.config.mode in [AgentMode.REASONING, AgentMode.HYBRID]
                )
                
                # Call LLM to decide tool usage
                llm_response = await self._call_llm(
                    messages=messages,
                    tools=available_tools,
                    stream=False
                )
                
                # Parse and execute tool calls
                tool_calls = self._parse_tool_calls(llm_response)
                
                for tool_call in tool_calls[:self.config.max_tool_calls]:
                    reasoning_steps.append(f"Gọi tool: {tool_call['name']}")
                    
                    # Execute tool
                    result = await self.tool_registry.execute(
                        tool_name=tool_call["name"],
                        **tool_call.get("arguments", {})
                    )
                    
                    tool_results.append(result)
                    tool_calls_made.append({
                        "name": tool_call["name"],
                        "arguments": tool_call.get("arguments", {}),
                        "result": result.to_dict()
                    })
                    
                    # Add tool result to memory
                    self.memory.add_message_to_session(
                        session_id=session_id,
                        role="tool",
                        content=json.dumps(result.data, ensure_ascii=False) if result.success else result.error,
                        metadata={
                            "tool_call_id": tool_call.get("id"),
                            "tool_name": tool_call["name"]
                        }
                    )
                    
                    # Extract sources if search tool
                    if tool_call["name"] == "search_knowledge" and result.success:
                        if isinstance(result.data, dict) and "results" in result.data:
                            for r in result.data["results"]:
                                if "source" in r:
                                    sources.append({
                                        "content": r.get("content", "")[:200],
                                        "source": r.get("source", "unknown"),
                                        "score": r.get("score", 0)
                                    })
                    
                    reasoning_steps.append(f"Kết quả: {result.tool_name} - {'OK' if result.success else result.error}")
            
            # === FINAL RESPONSE PHASE ===
            # Build final messages with tool results
            messages = self._build_messages(
                session_id=session_id,
                include_tool_results=True,
                reasoning=self.config.mode in [AgentMode.REASONING, AgentMode.HYBRID]
            )
            
            # Generate final response
            final_content = await self._generate_response(messages)
            
            # Add assistant response to memory
            self.memory.add_message_to_session(
                session_id=session_id,
                role="assistant",
                content=final_content,
                tool_calls=tool_calls_made if tool_calls_made else None,
                tool_results=[r.to_dict() for r in tool_results] if tool_results else None
            )
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AgentResponse(
                content=final_content,
                session_id=session_id,
                tool_calls=tool_calls_made,
                tool_results=tool_results,
                reasoning_steps=reasoning_steps,
                sources=sources,
                metadata={
                    "model": self.config.model,
                    "mode": self.config.mode.value,
                    "tokens_used": 0  # TODO: track tokens
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return AgentResponse(
                content=f"Đã xảy ra lỗi: {str(e)}",
                session_id=session_id,
                tool_calls=tool_calls_made,
                tool_results=tool_results,
                reasoning_steps=reasoning_steps,
                sources=sources,
                metadata={},
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    def _build_messages(
        self,
        session_id: str,
        include_tool_results: bool = False,
        reasoning: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Build messages list cho LLM.
        
        Args:
            session_id: Session ID
            include_tool_results: Include tool results in messages
            reasoning: Include reasoning prompt
            
        Returns:
            List of message dicts
        """
        messages = []
        
        # System prompt
        system_content = self.config.system_prompt
        if reasoning:
            system_content += "\n\n" + self.config.reasoning_prompt
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Short-term memory context
        short_term = self.memory.get_short_term_memory(session_id)
        if short_term:
            memory_context = "Thông tin đã biết:\n"
            for item in short_term:
                memory_context += f"- {item['key']}: {item['value']}\n"
            messages.append({
                "role": "system",
                "content": memory_context
            })
        
        # Conversation history
        context_messages = self.memory.get_context_for_llm(
            session_id=session_id,
            max_messages=self.memory.config.max_context_messages
        )
        
        for msg in context_messages:
            # Skip tool messages if not including results
            if msg["role"] == "tool" and not include_tool_results:
                continue
            messages.append(msg)
        
        return messages
    
    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Any] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Gọi LLM API.
        
        Args:
            messages: List of messages
            tools: Available tools
            stream: Enable streaming
            
        Returns:
            LLM response
        """
        if self._use_mock_llm:
            return self._mock_llm_response(messages, tools)
        
        # Prepare request
        request_kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        if tools:
            request_kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters
                    }
                }
                for t in tools
            ]
        
        try:
            if stream:
                # Streaming response
                response = await self._llm_client.chat.completions.create(**request_kwargs)
                return response  # TODO: handle streaming
            else:
                response = await self._llm_client.chat.completions.create(**request_kwargs)
                
                return {
                    "content": response.choices[0].message.content,
                    "tool_calls": response.choices[0].message.tool_calls,
                    "finish_reason": response.choices[0].finish_reason
                }
                
        except Exception as e:
            # Fallback to mock on error
            return self._mock_llm_response(messages, tools)
    
    def _mock_llm_response(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Any] = None
    ) -> Dict[str, Any]:
        """
        Mock LLM response for testing/development.
        
        Args:
            messages: Input messages
            tools: Available tools
            
        Returns:
            Mock response
        """
        last_message = messages[-1]["content"] if messages else ""
        
        # Simple keyword detection
        if "tính" in last_message.lower() or "tính toán" in last_message.lower():
            # Return a mock tool call for calculator
            if tools:
                for t in tools:
                    if t.name == "calculate":
                        return {
                            "content": None,
                            "tool_calls": [{
                                "id": "call_mock_1",
                                "name": "calculate",
                                "arguments": {"expression": "100 * 1.1"}
                            }]
                        }
            
            return {
                "content": "Tôi sẽ tính toán cho bạn.",
                "tool_calls": None
            }
        
        if "tìm" in last_message.lower() or "thông tin" in last_message.lower() or "biết" in last_message.lower():
            if tools:
                for t in tools:
                    if t.name == "search_knowledge":
                        return {
                            "content": None,
                            "tool_calls": [{
                                "id": "call_mock_2",
                                "name": "search_knowledge",
                                "arguments": {"query": last_message, "limit": 3}
                            }]
                        }
        
        # Default response
        return {
            "content": f"Tôi đã nhận được: '{last_message}'. Đây là mock response.",
            "tool_calls": None
        }
    
    def _parse_tool_calls(self, llm_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse tool calls từ LLM response.
        
        Args:
            llm_response: Response từ LLM
            
        Returns:
            List of tool call dicts
        """
        tool_calls = []
        
        if not llm_response.get("tool_calls"):
            return tool_calls
        
        for tc in llm_response["tool_calls"]:
            if isinstance(tc, dict):
                # OpenAI format
                func = tc.get("function", {})
                tool_calls.append({
                    "id": tc.get("id"),
                    "name": func.get("name"),
                    "arguments": json.loads(func.get("arguments", "{}"))
                })
            else:
                # Other format
                tool_calls.append({
                    "id": getattr(tc, "id", "unknown"),
                    "name": getattr(tc, "name", "unknown"),
                    "arguments": getattr(tc, "arguments", {})
                })
        
        return tool_calls
    
    async def _generate_response(self, messages: List[Dict[str, Any]]) -> str:
        """
        Generate final response từ LLM.
        
        Args:
            messages: Messages including tool results
            
        Returns:
            Generated response string
        """
        response = await self._call_llm(messages=messages, tools=None, stream=False)
        return response.get("content", "Không có phản hồi từ AI.")
    
    # === Tool Management ===
    def register_tool(self, tool: Any) -> None:
        """Register a tool với agent."""
        self.tool_registry.register(tool)
    
    def list_tools(self) -> List[str]:
        """List all registered tools."""
        return self.tool_registry.list_tools()
    
    # === Session Management ===
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get session by ID."""
        return self.memory.get_session(session_id)
    
    def export_session(self, session_id: str) -> Optional[str]:
        """Export session to JSON."""
        return self.memory.export_session(session_id)
    
    def import_session(self, json_str: str) -> Optional[ConversationContext]:
        """Import session from JSON."""
        return self.memory.import_session(json_str)
    
    @property
    def is_ready(self) -> bool:
        """Check if agent is ready (has LLM client)."""
        return not self._use_mock_llm

    # Alias for main.py compatibility
    async def chat(
        self,
        question: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        session_id: Optional[str] = None,
        mode: Optional[AgentMode] = None,
    ) -> Dict[str, Any]:
        """
        Alias for process(). Provided for main.py compatibility.
        
        Args:
            question: User question
            user_id: Optional user ID
            email: Optional email
            session_id: Session ID (auto-generated if None)
            mode: Agent mode (default: HYBRID)
            
        Returns:
            Dict with answer, sources, used_crm
        """
        # Generate session_id if not provided
        if not session_id:
            import uuid
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        # Handle optional AgentMode
        if mode is None:
            mode = AgentMode.HYBRID
        elif isinstance(mode, str):
            mode = AgentMode(mode.lower())
        
        # Temporarily set mode if different
        original_mode = self.config.mode
        if mode != original_mode:
            self.config.mode = mode
        
        try:
            result = await self.process(
                user_input=question,
                session_id=session_id,
                user_id=user_id,
            )
            
            # Convert AgentResponse to dict
            return {
                "answer": result.content,
                "sources": result.sources,
                "used_crm": False,  # Detected by agent internally
                "session_id": session_id,
            }
        finally:
            if mode != original_mode:
                self.config.mode = original_mode
