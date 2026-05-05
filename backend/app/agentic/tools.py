"""
Tool System cho Agent.
Định nghĩa các tools mà agent có thể sử dụng.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..rag.retriever import HybridRetriever


class ToolCategory(Enum):
    """Phân loại tool theo chức năng."""
    SEARCH = "search"           # Tìm kiếm thông tin
    CRM = "crm"                 # Thao tác CRM
    CALCULATOR = "calculator"   # Tính toán
    UTILITY = "utility"         # Tiện ích khác


@dataclass
class ToolDefinition:
    """
    Định nghĩa cấu trúc của một tool.
    """
    name: str                          # Tên tool (unique)
    description: str                    # Mô tả chức năng
    category: ToolCategory              # Phân loại tool
    parameters: Dict[str, Any]         # Schema tham số (JSON schema style)
    function: Callable[..., Any]        # Hàm thực thi
    is_async: bool = False             # Tool có phải async không
    timeout: Optional[float] = 30.0    # Timeout cho tool execution


@dataclass
class ToolResult:
    """
    Kết quả trả về từ tool execution.
    """
    tool_name: str                     # Tên tool đã thực thi
    success: bool                      # Thành công hay không
    data: Any = None                   # Dữ liệu trả về
    error: Optional[str] = None        # Lỗi nếu có
    execution_time: float = 0.0       # Thời gian thực thi (ms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sang dict để truyền cho LLM."""
        return {
            "tool": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time
        }


class Tool(ABC):
    """
    Base class cho tất cả tools.
    Inherit từ class này để tạo tool mới.
    """
    
    # Override these in subclass
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    parameters_schema: Dict[str, Any] = {}
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Thực thi tool với các arguments.
        Override in subclass.
        """
        pass
    
    async def execute_with_timeout(self, timeout: float = 30.0, **kwargs) -> ToolResult:
        """
        Execute tool với timeout handling.
        """
        import time
        start_time = time.perf_counter()
        
        try:
            if asyncio.iscoroutinefunction(self.execute):
                result = await asyncio.wait_for(self.execute(**kwargs), timeout=timeout)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor, 
                    lambda: self.execute(**kwargs)
                )
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=result,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            execution_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Tool execution timed out after {timeout}s",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def get_definition(self) -> ToolDefinition:
        """Lấy tool definition cho việc đăng ký."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=self.parameters_schema,
            function=self.execute,
            is_async=asyncio.iscoroutinefunction(self.execute)
        )


class SearchTool(Tool):
    """
    Tool để tìm kiếm thông tin từ RAG system.
    """
    name = "search_knowledge"
    description = "Tìm kiếm thông tin từ knowledge base nội bộ. Sử dụng khi user hỏi về thông tin công ty, chính sách, quy trình, sản phẩm."
    category = ToolCategory.SEARCH
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Câu hỏi hoặc từ khóa tìm kiếm"
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng kết quả trả về",
                "default": 5
            },
            "score_threshold": {
                "type": "number",
                "description": "Ngưỡng similarity score tối thiểu",
                "default": 0.5
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, retriever: HybridRetriever):
        super().__init__()
        self.retriever = retriever
    
    async def execute(self, query: str, limit: int = 5, score_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Thực hiện tìm kiếm.
        
        Args:
            query: Câu hỏi từ user
            limit: Số lượng kết quả
            score_threshold: Ngưỡng similarity
            
        Returns:
            Kết quả tìm kiếm với sources
        """
        results = await self.retriever.retrieve(
            query=query,
            limit=limit,
            score_threshold=score_threshold
        )
        
        if not results:
            return {
                "query": query,
                "results": [],
                "total": 0,
                "message": "Không tìm thấy thông tin phù hợp"
            }
        
        # Format kết quả
        formatted_results = []
        for r in results:
            formatted_results.append({
                "content": r.get("payload", {}).get("content", ""),
                "source": r.get("payload", {}).get("source", "unknown"),
                "score": r.get("score", 0),
                "metadata": r.get("payload", {}).get("metadata", {})
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total": len(formatted_results),
            "message": f"Tìm thấy {len(formatted_results)} kết quả phù hợp"
        }


class CalculatorTool(Tool):
    """
    Tool để thực hiện các phép tính đơn giản.
    """
    name = "calculate"
    description = "Thực hiện các phép tính toán học. Sử dụng khi user cần tính toán các con số."
    category = ToolCategory.CALCULATOR
    parameters_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Biểu thức toán cần tính (VD: '100 * 1.1 + 50')"
            }
        },
        "required": ["expression"]
    }
    
    async def execute(self, expression: str) -> Dict[str, Any]:
        """
        Thực hiện tính toán.
        
        Args:
            expression: Biểu thức toán học
            
        Returns:
            Kết quả tính toán
        """
        try:
            # An toàn hơn với eval - chỉ cho phép operators cơ bản
            allowed_chars = set("0123456789.+-*/()%e ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Biểu thức chứa ký tự không được phép")
            
            result = eval(expression, {"__builtins__": {}}, {})
            
            return {
                "expression": expression,
                "result": result,
                "success": True
            }
        except ZeroDivisionError:
            return {
                "expression": expression,
                "result": None,
                "success": False,
                "error": "Lỗi: chia cho zero"
            }
        except Exception as e:
            return {
                "expression": expression,
                "result": None,
                "success": False,
                "error": f"Lỗi tính toán: {str(e)}"
            }


class CRMCalculatorTool(Tool):
    """
    Tool để tính toán liên quan đến CRM (doanh số, commission, v.v.).
    """
    name = "crm_calculate"
    description = "Tính toán các chỉ số kinh doanh như commission, doanh số, thưởng. Sử dụng khi user hỏi về tính toán liên quan đến sales/CRM."
    category = ToolCategory.CALCULATOR
    parameters_schema = {
        "type": "object",
        "properties": {
            "calculation_type": {
                "type": "string",
                "enum": ["commission", "revenue", "target", "discount"],
                "description": "Loại tính toán"
            },
            "params": {
                "type": "object",
                "description": "Các tham số cho tính toán"
            }
        },
        "required": ["calculation_type", "params"]
    }
    
    # Commission rates theo tier
    COMMISSION_RATES = {
        "tier_1": 0.10,   # 10% cho doanh số < 50M
        "tier_2": 0.15,   # 15% cho doanh số 50M-100M
        "tier_3": 0.20,   # 20% cho doanh số > 100M
    }
    
    async def execute(self, calculation_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực hiện tính toán CRM.
        
        Args:
            calculation_type: Loại tính toán
            params: Tham số
        """
        if calculation_type == "commission":
            return self._calculate_commission(params)
        elif calculation_type == "revenue":
            return self._calculate_revenue(params)
        elif calculation_type == "target":
            return self._calculate_target(params)
        elif calculation_type == "discount":
            return self._calculate_discount(params)
        else:
            return {"success": False, "error": f"Unknown calculation type: {calculation_type}"}
    
    def _calculate_commission(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tính commission cho sales person."""
        revenue = params.get("revenue", 0)
        tier = params.get("tier", "tier_1")
        
        rate = self.COMMISSION_RATES.get(tier, 0.10)
        commission = revenue * rate
        
        return {
            "calculation": "commission",
            "revenue": revenue,
            "tier": tier,
            "rate": rate,
            "commission": commission,
            "success": True
        }
    
    def _calculate_revenue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tính doanh số từ các deals."""
        deals = params.get("deals", [])
        total = sum(deal.get("value", 0) for deal in deals)
        
        return {
            "calculation": "revenue",
            "deal_count": len(deals),
            "total_revenue": total,
            "average_deal": total / len(deals) if deals else 0,
            "success": True
        }
    
    def _calculate_target(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tính achievement percentage."""
        target = params.get("target", 0)
        actual = params.get("actual", 0)
        
        achievement = (actual / target * 100) if target > 0 else 0
        
        return {
            "calculation": "target",
            "target": target,
            "actual": actual,
            "achievement_percent": round(achievement, 2),
            "status": "exceeded" if achievement > 100 else "achieved" if achievement >= 100 else "pending",
            "success": True
        }
    
    def _calculate_discount(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tính giá sau discount."""
        original_price = params.get("original_price", 0)
        discount_percent = params.get("discount_percent", 0)
        
        discount_amount = original_price * (discount_percent / 100)
        final_price = original_price - discount_amount
        
        return {
            "calculation": "discount",
            "original_price": original_price,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "final_price": final_price,
            "success": True
        }


class ToolRegistry:
    """
    Registry quản lý tất cả tools có sẵn cho agent.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
    
    def register(self, tool: Tool) -> None:
        """
        Đăng ký một tool.
        
        Args:
            tool: Tool instance
        """
        definition = tool.get_definition()
        self._tools[definition.name] = tool
        self._definitions[definition.name] = definition
    
    def register_by_name(self, name: str, func: Callable, description: str = "", 
                         parameters: Dict[str, Any] = None, is_async: bool = False) -> None:
        """
        Đăng ký tool bằng cách truyền trực tiếp function.
        
        Args:
            name: Tên tool
            func: Function thực thi
            description: Mô tả
            parameters: Schema tham số
            is_async: Có phải async function không
        """
        self._tools[name] = func
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            category=ToolCategory.UTILITY,
            parameters=parameters or {},
            function=func,
            is_async=is_async
        )
    
    def get(self, name: str) -> Optional[Tool]:
        """Lấy tool theo tên."""
        return self._tools.get(name)
    
    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        """Lấy tool definition."""
        return self._definitions.get(name)
    
    def get_all_definitions(self) -> List[ToolDefinition]:
        """Lấy tất cả tool definitions."""
        return list(self._definitions.values())
    
    def get_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Lấy tools theo category."""
        return [d for d in self._definitions.values() if d.category == category]
    
    def list_tools(self) -> List[str]:
        """Liệt kê tên tất cả tools."""
        return list(self._tools.keys())
    
    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Thực thi tool theo tên.
        
        Args:
            tool_name: Tên tool
            **kwargs: Arguments cho tool
            
        Returns:
            ToolResult
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found"
            )
        
        if isinstance(tool, Tool):
            return await tool.execute_with_timeout(**kwargs)
        else:
            # Direct function
            import time
            start = time.perf_counter()
            try:
                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**kwargs)
                else:
                    result = tool(**kwargs)
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    data=result,
                    execution_time=(time.perf_counter() - start) * 1000
                )
            except Exception as e:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=str(e),
                    execution_time=(time.perf_counter() - start) * 1000
                )
    
    def remove(self, name: str) -> bool:
        """Xóa tool khỏi registry."""
        if name in self._tools:
            del self._tools[name]
            del self._definitions[name]
            return True
        return False
