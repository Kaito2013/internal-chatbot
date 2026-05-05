"""
CRM Tool cho Agent.
Wrapper để expose CRM operations như tools cho agent.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from .tools import Tool, ToolCategory
from ..crm.base import (
    BaseCRMClient,
    CRMContact,
    CRMDeal,
    CRMCompany,
    CRMTask,
    CRMConfig,
)
from ..crm.factory import CRMClientFactory, CRMProvider


class BaseCRMOperationTool(Tool):
    """
    Base class cho CRM tools.
    """
    
    def __init__(self, crm_client: BaseCRMClient):
        super().__init__()
        self.crm_client = crm_client


class SearchContactTool(BaseCRMOperationTool):
    """
    Tool để tìm kiếm contacts trong CRM.
    """
    name = "crm_search_contact"
    description = """Tìm kiếm contact/lead trong CRM system.
Sử dụng khi user hỏi về thông tin khách hàng, tìm contact, tra cứu khách hàng.
Có thể tìm bằng tên, email, số điện thoại, hoặc tên công ty."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Từ khóa tìm kiếm (tên, email, công ty)"
            },
            "email": {
                "type": "string",
                "description": "Tìm theo email cụ thể"
            },
            "phone": {
                "type": "string",
                "description": "Tìm theo số điện thoại"
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa",
                "default": 10
            }
        }
    }
    
    async def execute(
        self,
        query: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Tìm kiếm contacts.
        
        Args:
            query: Từ khóa tìm kiếm
            email: Email cụ thể
            phone: Số điện thoại
            limit: Max results
            
        Returns:
            Kết quả tìm kiếm
        """
        contacts = await self.crm_client.search_contacts(
            query=query,
            email=email,
            phone=phone,
            limit=limit
        )
        
        if not contacts:
            return {
                "success": True,
                "results": [],
                "message": "Không tìm thấy contact nào"
            }
        
        return {
            "success": True,
            "results": [c.to_dict() for c in contacts],
            "count": len(contacts),
            "message": f"Tìm thấy {len(contacts)} contact(s)"
        }


class GetContactDetailTool(BaseCRMOperationTool):
    """
    Tool để lấy chi tiết một contact.
    """
    name = "crm_get_contact"
    description = """Lấy thông tin chi tiết của một contact/lead từ CRM.
Sử dụng khi đã có contact_id hoặc cần xem thông tin cụ thể của một khách hàng."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "contact_id": {
                "type": "string",
                "description": "Contact ID cần lấy thông tin"
            }
        },
        "required": ["contact_id"]
    }
    
    async def execute(self, contact_id: str) -> Dict[str, Any]:
        """
        Lấy contact details.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            Contact details
        """
        contact = await self.crm_client.get_contact(contact_id)
        
        if not contact:
            return {
                "success": False,
                "error": f"Không tìm thấy contact với ID: {contact_id}"
            }
        
        return {
            "success": True,
            "contact": contact.to_dict()
        }


class SearchDealTool(BaseCRMOperationTool):
    """
    Tool để tìm kiếm deals/opportunities.
    """
    name = "crm_search_deal"
    description = """Tìm kiếm deals/opportunities trong CRM.
Sử dụng khi user hỏi về deals, cơ hội bán hàng, hợp đồng, hoặc tình trạng deal."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Từ khóa tìm kiếm (tên deal, công ty)"
            },
            "stage": {
                "type": "string",
                "description": "Filter theo stage (prospecting, proposal, negotiation, closed_won, closed_lost)"
            },
            "owner_id": {
                "type": "string",
                "description": "Filter theo owner ID"
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa",
                "default": 10
            }
        }
    }
    
    async def execute(
        self,
        query: Optional[str] = None,
        stage: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Tìm kiếm deals.
        
        Args:
            query: Từ khóa tìm kiếm
            stage: Filter theo stage
            owner_id: Filter theo owner
            limit: Max results
            
        Returns:
            Kết quả tìm kiếm
        """
        deals = await self.crm_client.search_deals(
            query=query,
            stage=stage,
            owner_id=owner_id,
            limit=limit
        )
        
        if not deals:
            return {
                "success": True,
                "results": [],
                "message": "Không tìm thấy deal nào"
            }
        
        # Calculate total amount
        total_amount = sum(d.amount for d in deals)
        
        return {
            "success": True,
            "results": [d.to_dict() for d in deals],
            "count": len(deals),
            "total_amount": total_amount,
            "message": f"Tìm thấy {len(deals)} deal(s), tổng giá trị: {total_amount:,.0f} VND"
        }


class GetDealDetailTool(BaseCRMOperationTool):
    """
    Tool để lấy chi tiết một deal.
    """
    name = "crm_get_deal"
    description = """Lấy thông tin chi tiết của một deal/opportunity từ CRM.
Sử dụng khi đã có deal_id hoặc cần xem thông tin cụ thể của một deal."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "deal_id": {
                "type": "string",
                "description": "Deal ID cần lấy thông tin"
            }
        },
        "required": ["deal_id"]
    }
    
    async def execute(self, deal_id: str) -> Dict[str, Any]:
        """
        Lấy deal details.
        
        Args:
            deal_id: Deal ID
            
        Returns:
            Deal details
        """
        deal = await self.crm_client.get_deal(deal_id)
        
        if not deal:
            return {
                "success": False,
                "error": f"Không tìm thấy deal với ID: {deal_id}"
            }
        
        return {
            "success": True,
            "deal": deal.to_dict()
        }


class SearchCompanyTool(BaseCRMOperationTool):
    """
    Tool để tìm kiếm companies/accounts.
    """
    name = "crm_search_company"
    description = """Tìm kiếm companies/accounts trong CRM.
Sử dụng khi user hỏi về thông tin công ty, tìm kiếm doanh nghiệp."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Từ khóa tìm kiếm (tên công ty, website)"
            },
            "industry": {
                "type": "string",
                "description": "Filter theo ngành (Technology, Manufacturing, Retail, etc.)"
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa",
                "default": 10
            }
        }
    }
    
    async def execute(
        self,
        query: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Tìm kiếm companies.
        
        Args:
            query: Từ khóa tìm kiếm
            industry: Filter theo ngành
            limit: Max results
            
        Returns:
            Kết quả tìm kiếm
        """
        companies = await self.crm_client.search_companies(
            query=query,
            industry=industry,
            limit=limit
        )
        
        if not companies:
            return {
                "success": True,
                "results": [],
                "message": "Không tìm thấy công ty nào"
            }
        
        return {
            "success": True,
            "results": [c.to_dict() for c in companies],
            "count": len(companies),
            "message": f"Tìm thấy {len(companies)} công ty"
        }


class GetSalesPipelineTool(BaseCRMOperationTool):
    """
    Tool để lấy sales pipeline.
    """
    name = "crm_get_pipeline"
    description = """Lấy thông tin sales pipeline từ CRM.
Hiển thị các deals theo từng stage của pipeline.
Sử dụng khi user hỏi về pipeline, tình trạng deals theo stage."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline ID cụ thể (optional)"
            }
        }
    }
    
    async def execute(self, pipeline_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy sales pipeline.
        
        Args:
            pipeline_id: Pipeline ID
            
        Returns:
            Pipeline data
        """
        opportunities = await self.crm_client.get_sales_pipeline(pipeline_id)
        
        # Group by stage
        stages: Dict[str, List[Dict]] = {}
        for opp in opportunities:
            stage = opp.stage_name or "unknown"
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(opp.to_dict())
        
        # Calculate totals
        total_amount = sum(opp.amount for opp in opportunities)
        total_count = len(opportunities)
        
        return {
            "success": True,
            "pipeline": stages,
            "summary": {
                "total_opportunities": total_count,
                "total_amount": total_amount,
                "stages_count": len(stages)
            },
            "message": f"Pipeline có {total_count} opportunities, tổng giá trị: {total_amount:,.0f} VND"
        }


class GetSalesSummaryTool(BaseCRMOperationTool):
    """
    Tool để lấy sales summary/report.
    """
    name = "crm_get_sales_summary"
    description = """Lấy báo cáo tổng hợp về sales từ CRM.
Bao gồm thông tin về tổng deals, doanh số, win rate.
Sử dụng khi user hỏi về báo cáo sales, tổng kết kinh doanh."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Start date (ISO format: YYYY-MM-DD)"
            },
            "end_date": {
                "type": "string",
                "description": "End date (ISO format: YYYY-MM-DD)"
            },
            "owner_id": {
                "type": "string",
                "description": "Filter theo owner ID"
            }
        }
    }
    
    async def execute(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy sales summary.
        
        Args:
            start_date: Start date string
            end_date: End date string
            owner_id: Owner filter
            
        Returns:
            Sales summary
        """
        # Parse dates
        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date)
        if end_date:
            end = datetime.fromisoformat(end_date)
        
        summary = await self.crm_client.get_sales_summary(
            start_date=start,
            end_date=end,
            owner_id=owner_id
        )
        
        return {
            "success": True,
            "summary": summary,
            "message": f"Tổng quan: {summary['total_deals']} deals, Win rate: {summary['win_rate']:.1f}%"
        }


class GetTasksTool(BaseCRMOperationTool):
    """
    Tool để lấy tasks từ CRM.
    """
    name = "crm_get_tasks"
    description = """Lấy danh sách tasks từ CRM.
Có thể filter theo contact, deal, hoặc status.
Sử dụng khi user hỏi về công việc, task, reminders."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "contact_id": {
                "type": "string",
                "description": "Filter theo contact ID"
            },
            "deal_id": {
                "type": "string",
                "description": "Filter theo deal ID"
            },
            "status": {
                "type": "string",
                "description": "Filter theo status (pending, in_progress, completed, cancelled)"
            },
            "limit": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa",
                "default": 20
            }
        }
    }
    
    async def execute(
        self,
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Lấy tasks.
        
        Args:
            contact_id: Contact filter
            deal_id: Deal filter
            status: Status filter
            limit: Max results
            
        Returns:
            Tasks list
        """
        tasks = await self.crm_client.get_tasks(
            contact_id=contact_id,
            deal_id=deal_id,
            status=status,
            limit=limit
        )
        
        if not tasks:
            return {
                "success": True,
                "results": [],
                "message": "Không tìm thấy task nào"
            }
        
        return {
            "success": True,
            "results": [t.to_dict() for t in tasks],
            "count": len(tasks),
            "message": f"Tìm thấy {len(tasks)} task(s)"
        }


class CreateCRMTaskTool(BaseCRMOperationTool):
    """
    Tool để tạo task mới trong CRM.
    """
    name = "crm_create_task"
    description = """Tạo task/công việc mới trong CRM.
Sử dụng khi user yêu cầu tạo reminder, task, follow-up."""
    category = ToolCategory.CRM
    parameters_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Tiêu đề task"
            },
            "description": {
                "type": "string",
                "description": "Mô tả chi tiết"
            },
            "task_type": {
                "type": "string",
                "description": "Loại task (call, email, meeting, follow_up, other)",
                "default": "follow_up"
            },
            "priority": {
                "type": "string",
                "description": "Độ ưu tiên (low, medium, high, urgent)",
                "default": "medium"
            },
            "due_date": {
                "type": "string",
                "description": "Ngày hạn (ISO format: YYYY-MM-DD)"
            },
            "contact_id": {
                "type": "string",
                "description": "Contact ID liên quan"
            },
            "deal_id": {
                "type": "string",
                "description": "Deal ID liên quan"
            }
        },
        "required": ["title"]
    }
    
    async def execute(
        self,
        title: str,
        description: Optional[str] = None,
        task_type: str = "follow_up",
        priority: str = "medium",
        due_date: Optional[str] = None,
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo task mới.
        
        Args:
            title: Task title
            description: Description
            task_type: Task type
            priority: Priority
            due_date: Due date string
            contact_id: Related contact
            deal_id: Related deal
            
        Returns:
            Created task
        """
        task = CRMTask(
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            contact_id=contact_id,
            deal_id=deal_id
        )
        
        if due_date:
            task.due_date = datetime.fromisoformat(due_date)
        
        created_task = await self.crm_client.create_task(task)
        
        return {
            "success": True,
            "task": created_task.to_dict(),
            "message": f"Đã tạo task: {title}"
        }


class CRMToolRegistry:
    """
    Registry chứa tất cả CRM tools.
    Tiện lợi để đăng ký tất cả tools cùng lúc.
    """
    
    def __init__(self, crm_client: BaseCRMClient):
        """
        Khởi tạo CRM Tool Registry.
        
        Args:
            crm_client: CRM client instance
        """
        self.crm_client = crm_client
        self._tools = {
            "crm_search_contact": SearchContactTool(crm_client),
            "crm_get_contact": GetContactDetailTool(crm_client),
            "crm_search_deal": SearchDealTool(crm_client),
            "crm_get_deal": GetDealDetailTool(crm_client),
            "crm_search_company": SearchCompanyTool(crm_client),
            "crm_get_pipeline": GetSalesPipelineTool(crm_client),
            "crm_get_sales_summary": GetSalesSummaryTool(crm_client),
            "crm_get_tasks": GetTasksTool(crm_client),
            "crm_create_task": CreateCRMTaskTool(crm_client),
        }
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Lấy tool theo tên."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Lấy tất cả tools."""
        return list(self._tools.values())
    
    def list_tool_names(self) -> List[str]:
        """Liệt kê tên tools."""
        return list(self._tools.keys())


def create_crm_tools(crm_config: Optional[CRMConfig] = None, 
                     use_mock: bool = True) -> CRMToolRegistry:
    """
    Factory function để tạo CRM tools.
    
    Args:
        crm_config: CRM configuration
        use_mock: Dùng mock CRM client
        
    Returns:
        CRMToolRegistry instance
    """
    client = CRMClientFactory.create_client(
        provider=crm_config.provider if crm_config else CRMProvider.GENERIC,
        config=crm_config,
        use_mock=use_mock
    )
    
    return CRMToolRegistry(client)
