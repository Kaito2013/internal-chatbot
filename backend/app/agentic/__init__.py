"""
Agentic Layer - Module khởi tạo.
Chứa các components cho agentic AI system.
"""
from .agent import Agent, AgentConfig, AgentResponse, AgentMode, ReasoningStrategy
from .memory import (
    ConversationMemory,
    MemoryConfig,
    ConversationContext,
    Message,
    MemoryType,
)
from .tools import Tool, ToolResult, ToolRegistry, ToolCategory, ToolDefinition
from .crm_tool import (
    CRMToolRegistry,
    create_crm_tools,
    BaseCRMOperationTool,
    SearchContactTool,
    GetContactDetailTool,
    SearchDealTool,
    GetDealDetailTool,
    SearchCompanyTool,
    GetSalesPipelineTool,
    GetSalesSummaryTool,
    GetTasksTool,
    CreateCRMTaskTool,
)

__all__ = [
    # Agent core
    "Agent",
    "AgentConfig",
    "AgentResponse",
    "AgentMode",
    "ReasoningStrategy",
    # Memory
    "ConversationMemory",
    "MemoryConfig",
    "ConversationContext",
    "Message",
    "MemoryType",
    # Tools
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ToolCategory",
    "ToolDefinition",
    # CRM Tools
    "CRMToolRegistry",
    "create_crm_tools",
    "BaseCRMOperationTool",
    "SearchContactTool",
    "GetContactDetailTool",
    "SearchDealTool",
    "GetDealDetailTool",
    "SearchCompanyTool",
    "GetSalesPipelineTool",
    "GetSalesSummaryTool",
    "GetTasksTool",
    "CreateCRMTaskTool",
]
