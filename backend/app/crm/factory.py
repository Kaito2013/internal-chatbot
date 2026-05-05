"""
CRM Client Factory.
Tạo CRM client theo provider.
"""
from typing import Any, Dict, Optional
import logging

from .base import (
    BaseCRMClient,
    CRMConfig,
    CRMProvider,
    CRMContact,
    CRMDeal,
    CRMCompany,
    CRMTask,
)
from .mock_client import MockCRMClient

logger = logging.getLogger(__name__)


class CRMClientFactory:
    """
    Factory để tạo CRM client theo provider.
    
    Usage:
        factory = CRMClientFactory()
        client = factory.create_client(
            provider=CRMProvider.SALESFORCE,
            config=CRMConfig(api_key="...", ...)
        )
    """
    
    _clients: Dict[CRMProvider, type] = {
        CRMProvider.SALESFORCE: None,  # Will be implemented
        CRMProvider.HUBSPOT: None,     # Will be implemented
        CRMProvider.ZOHO: None,        # Will be implemented
        CRMProvider.PIPEDRIVE: None,   # Will be implemented
        CRMProvider.GENERIC: None,     # Will be implemented
    }
    
    @classmethod
    def register(cls, provider: CRMProvider, client_class: type) -> None:
        """
        Register a CRM client class.
        
        Args:
            provider: CRM provider type
            client_class: Client class (must inherit from BaseCRMClient)
        """
        if not issubclass(client_class, BaseCRMClient):
            raise ValueError(f"{client_class} must inherit from BaseCRMClient")
        cls._clients[provider] = client_class
        logger.info(f"Registered CRM client for provider: {provider.value}")
    
    @classmethod
    def create_client(
        cls,
        provider: CRMProvider,
        config: Optional[CRMConfig] = None,
        use_mock: bool = False,
        **kwargs
    ) -> BaseCRMClient:
        """
        Tạo CRM client instance.
        
        Args:
            provider: CRM provider type
            config: CRM configuration
            use_mock: Nếu True, dùng mock client
            **kwargs: Additional config parameters
            
        Returns:
            CRM client instance
            
        Raises:
            ValueError: Nếu provider không được hỗ trợ
        """
        if config is None:
            config = CRMConfig(provider=provider, **kwargs)
        
        # Use mock if requested or if client not registered
        if use_mock or cls._clients.get(provider) is None:
            logger.info(f"Using mock CRM client for provider: {provider.value}")
            return MockCRMClient(config)
        
        client_class = cls._clients[provider]
        return client_class(config)
    
    @classmethod
    def list_providers(cls) -> list:
        """Liệt kê các providers được hỗ trợ."""
        return [p.value for p in CRMProvider]
    
    @classmethod
    def is_provider_supported(cls, provider: CRMProvider) -> bool:
        """Kiểm tra provider có client implementation không."""
        return cls._clients.get(provider) is not None


class MockCRMClient(BaseCRMClient):
    """
    Mock CRM Client cho development và testing.
    Lưu trữ dữ liệu in-memory.
    """
    
    def __init__(self, config: CRMConfig):
        super().__init__(config)
        
        # In-memory storage
        self._contacts: Dict[str, CRMContact] = {}
        self._deals: Dict[str, CRMDeal] = {}
        self._companies: Dict[str, CRMCompany] = {}
        self._tasks: Dict[str, CRMTask] = {}
        
        # Counter for IDs
        self._id_counters = {
            "contact": 1000,
            "deal": 2000,
            "company": 3000,
            "task": 4000
        }
        
        # Initialize with sample data
        self._init_sample_data()
    
    def _init_sample_data(self) -> None:
        """Initialize với sample data."""
        from datetime import datetime, timedelta
        
        # Sample companies
        companies = [
            CRMCompany(
                id="comp_001",
                name="Công ty TNHH ABC",
                legal_name="Công ty TNHH ABC Việt Nam",
                industry="Technology",
                phone="028-1234-5678",
                email="contact@abc.vn",
                website="https://abc.vn",
                revenue=50000000000,
                company_size="100-500",
                billing_city="Hồ Chí Minh",
                billing_country="Vietnam"
            ),
            CRMCompany(
                id="comp_002",
                name="Tập đoàn XYZ",
                legal_name="Tập đoàn XYZ Corporation",
                industry="Manufacturing",
                phone="024-9876-5432",
                email="info@xyz.com",
                website="https://xyz.com",
                revenue=200000000000,
                company_size="1000+",
                billing_city="Hà Nội",
                billing_country="Vietnam"
            ),
            CRMCompany(
                id="comp_003",
                name="Công ty DEF",
                industry="Retail",
                phone="028-5555-1234",
                email="hello@def.vn",
                revenue=10000000000,
                company_size="50-100",
                billing_city="Đà Nẵng",
                billing_country="Vietnam"
            )
        ]
        
        for c in companies:
            self._companies[c.id] = c
        
        # Sample contacts
        contacts = [
            CRMContact(
                id="cont_001",
                first_name="Nguyễn",
                last_name="Văn An",
                email="an.nguyen@abc.vn",
                phone="0901-234-567",
                title="Giám đốc",
                department="Kinh doanh",
                company_id="comp_001",
                company_name="Công ty TNHH ABC",
                lead_source="Website",
                status="active"
            ),
            CRMContact(
                id="cont_002",
                first_name="Trần",
                last_name="Thị Bình",
                email="binh.tran@xyz.com",
                phone="0902-345-678",
                title="Trưởng phòng",
                department="Marketing",
                company_id="comp_002",
                company_name="Tập đoàn XYZ",
                lead_source=" Referral",
                status="active"
            ),
            CRMContact(
                id="cont_003",
                first_name="Lê",
                last_name="Văn Cường",
                email="cuong.le@abc.vn",
                phone="0903-456-789",
                title="Kỹ sư",
                department="IT",
                company_id="comp_001",
                company_name="Công ty TNHH ABC",
                lead_source="LinkedIn",
                status="active"
            )
        ]
        
        for c in contacts:
            self._contacts[c.id] = c
        
        # Sample deals
        deals = [
            CRMDeal(
                id="deal_001",
                title="Hợp đồng phần mềm ABC",
                amount=50000000,
                stage="negotiation",
                probability=75.0,
                expected_close_date=datetime.now() + timedelta(days=30),
                contact_id="cont_001",
                contact_name="Nguyễn Văn An",
                company_id="comp_001",
                company_name="Công ty TNHH ABC",
                owner_id="user_001",
                owner_name="Sales Rep 1",
                status="open"
            ),
            CRMDeal(
                id="deal_002",
                title="Dịch vụ tư vấn XYZ",
                amount=30000000,
                stage="proposal",
                probability=50.0,
                expected_close_date=datetime.now() + timedelta(days=45),
                contact_id="cont_002",
                contact_name="Trần Thị Bình",
                company_id="comp_002",
                company_name="Tập đoàn XYZ",
                owner_id="user_001",
                owner_name="Sales Rep 1",
                status="open"
            ),
            CRMDeal(
                id="deal_003",
                title="Thiết bị DEF",
                amount=80000000,
                stage="closed_won",
                probability=100.0,
                actual_close_date=datetime.now() - timedelta(days=10),
                contact_id="cont_001",
                contact_name="Nguyễn Văn An",
                company_id="comp_001",
                company_name="Công ty TNHH ABC",
                owner_id="user_002",
                owner_name="Sales Rep 2",
                status="won"
            )
        ]
        
        for d in deals:
            self._deals[d.id] = d
        
        # Sample tasks
        tasks = [
            CRMTask(
                id="task_001",
                title="Gọi điện cho khách hàng ABC",
                description="Follow up về hợp đồng",
                task_type="call",
                status="pending",
                priority="high",
                due_date=datetime.now() + timedelta(days=1),
                contact_id="cont_001",
                contact_name="Nguyễn Văn An",
                deal_id="deal_001"
            ),
            CRMTask(
                id="task_002",
                title="Gửi báo giá cho XYZ",
                description="Chuẩn bị báo giá chi tiết",
                task_type="email",
                status="in_progress",
                priority="medium",
                due_date=datetime.now() + timedelta(days=3),
                contact_id="cont_002",
                contact_name="Trần Thị Bình",
                deal_id="deal_002"
            )
        ]
        
        for t in tasks:
            self._tasks[t.id] = t
    
    def _generate_id(self, entity_type: str) -> str:
        """Generate new ID for entity type."""
        counter = self._id_counters.get(entity_type, 5000)
        counter += 1
        self._id_counters[entity_type] = counter
        return f"{entity_type}_{counter}"
    
    async def connect(self) -> bool:
        """Mock connect - luôn thành công."""
        return True
    
    async def disconnect(self) -> None:
        """Mock disconnect."""
        pass
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test mock connection."""
        return {
            "success": True,
            "provider": self.config.provider.value,
            "message": "Mock CRM connection successful",
            "contacts_count": len(self._contacts),
            "deals_count": len(self._deals),
            "companies_count": len(self._companies)
        }
    
    # === Contact Operations ===
    
    async def get_contact(self, contact_id: str) -> Optional[CRMContact]:
        return self._contacts.get(contact_id)
    
    async def search_contacts(
        self,
        query: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        limit: int = 20
    ) -> list:
        results = list(self._contacts.values())
        
        if query:
            q = query.lower()
            results = [
                c for c in results
                if q in (c.full_name.lower() if c.full_name else "")
                or q in (c.email.lower() if c.email else "")
                or q in (c.company_name.lower() if c.company_name else "")
            ]
        
        if email:
            results = [c for c in results if c.email and email.lower() in c.email.lower()]
        
        if phone:
            results = [c for c in results if c.phone and phone in c.phone]
        
        return results[:limit]
    
    async def create_contact(self, contact: CRMContact) -> CRMContact:
        if not contact.id:
            contact.id = self._generate_id("contact")
        self._contacts[contact.id] = contact
        return contact
    
    async def update_contact(self, contact: CRMContact) -> CRMContact:
        if contact.id and contact.id in self._contacts:
            self._contacts[contact.id] = contact
        return contact
    
    async def delete_contact(self, contact_id: str) -> bool:
        if contact_id in self._contacts:
            del self._contacts[contact_id]
            return True
        return False
    
    # === Deal Operations ===
    
    async def get_deal(self, deal_id: str) -> Optional[CRMDeal]:
        return self._deals.get(deal_id)
    
    async def search_deals(
        self,
        query: Optional[str] = None,
        stage: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 20
    ) -> list:
        results = list(self._deals.values())
        
        if query:
            q = query.lower()
            results = [
                d for d in results
                if q in (d.title.lower() if d.title else "")
                or q in (d.company_name.lower() if d.company_name else "")
            ]
        
        if stage:
            results = [d for d in results if d.stage == stage]
        
        if owner_id:
            results = [d for d in results if d.owner_id == owner_id]
        
        return results[:limit]
    
    async def create_deal(self, deal: CRMDeal) -> CRMDeal:
        if not deal.id:
            deal.id = self._generate_id("deal")
        self._deals[deal.id] = deal
        return deal
    
    async def update_deal(self, deal: CRMDeal) -> CRMDeal:
        if deal.id and deal.id in self._deals:
            self._deals[deal.id] = deal
        return deal
    
    async def delete_deal(self, deal_id: str) -> bool:
        if deal_id in self._deals:
            del self._deals[deal_id]
            return True
        return False
    
    # === Company Operations ===
    
    async def get_company(self, company_id: str) -> Optional[CRMCompany]:
        return self._companies.get(company_id)
    
    async def search_companies(
        self,
        query: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 20
    ) -> list:
        results = list(self._companies.values())
        
        if query:
            q = query.lower()
            results = [
                c for c in results
                if q in (c.name.lower() if c.name else "")
                or q in (c.website.lower() if c.website else "")
            ]
        
        if industry:
            results = [c for c in results if c.industry == industry]
        
        return results[:limit]
    
    async def create_company(self, company: CRMCompany) -> CRMCompany:
        if not company.id:
            company.id = self._generate_id("company")
        self._companies[company.id] = company
        return company
    
    async def update_company(self, company: CRMCompany) -> CRMCompany:
        if company.id and company.id in self._companies:
            self._companies[company.id] = company
        return company
    
    # === Task Operations ===
    
    async def get_tasks(
        self,
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> list:
        results = list(self._tasks.values())
        
        if contact_id:
            results = [t for t in results if t.contact_id == contact_id]
        
        if deal_id:
            results = [t for t in results if t.deal_id == deal_id]
        
        if status:
            results = [t for t in results if t.status == status]
        
        return results[:limit]
    
    async def create_task(self, task: CRMTask) -> CRMTask:
        if not task.id:
            task.id = self._generate_id("task")
        self._tasks[task.id] = task
        return task
    
    async def update_task(self, task: CRMTask) -> CRMTask:
        if task.id and task.id in self._tasks:
            self._tasks[task.id] = task
        return task
    
    async def complete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            self._tasks[task_id].status = "completed"
            from datetime import datetime
            self._tasks[task_id].completed_at = datetime.now()
            return True
        return False
    
    # === Dashboard & Reports ===
    
    async def get_sales_pipeline(self, pipeline_id: Optional[str] = None) -> list:
        """Return deals as pipeline opportunities."""
        from datetime import datetime
        
        opportunities = []
        for deal in self._deals.values():
            opp = CRMOpportunity(
                id=deal.id,
                name=deal.title,
                amount=deal.amount,
                currency=deal.currency,
                probability=deal.probability,
                expected_close_date=deal.expected_close_date,
                close_date=deal.actual_close_date,
                contact_id=deal.contact_id,
                contact_name=deal.contact_name,
                company_id=deal.company_id,
                company_name=deal.company_name,
                owner_id=deal.owner_id,
                owner_name=deal.owner_name,
                stage_name=deal.stage,
                created_at=deal.created_at
            )
            opportunities.append(opp)
        
        return opportunities
    
    async def get_sales_summary(
        self,
        start_date=None,
        end_date=None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate sales summary."""
        deals = list(self._deals.values())
        
        if owner_id:
            deals = [d for d in deals if d.owner_id == owner_id]
        
        total_amount = sum(d.amount for d in deals if d.status == "open")
        won_amount = sum(d.amount for d in deals if d.status == "won")
        lost_amount = sum(d.amount for d in deals if d.status == "lost")
        
        return {
            "total_deals": len(deals),
            "open_deals": len([d for d in deals if d.status == "open"]),
            "won_deals": len([d for d in deals if d.status == "won"]),
            "lost_deals": len([d for d in deals if d.status == "lost"]),
            "total_amount": total_amount,
            "won_amount": won_amount,
            "lost_amount": lost_amount,
            "win_rate": (len([d for d in deals if d.status == "won"]) / len(deals) * 100) if deals else 0
        }
