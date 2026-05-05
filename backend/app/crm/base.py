"""
CRM Base Classes và Data Models.
Định nghĩa interfaces và schemas cho CRM integration.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class CRMProvider(Enum):
    """CRM Provider types."""
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    ZOHO = "zoho"
    PIPEDRIVE = "pipedrive"
    GENERIC = "generic"  # Generic REST API


@dataclass
class CRMConfig:
    """Cấu hình kết nối CRM."""
    provider: CRMProvider = CRMProvider.GENERIC
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: str = "https://api.example.com"
    version: str = "v1"
    timeout: float = 30.0
    retry_attempts: int = 3
    
    # OAuth settings
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    # Custom headers
    headers: Dict[str, str] = field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True


# ============== Data Models ==============

@dataclass
class CRMContact:
    """CRM Contact/Lead model."""
    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    
    # Company link
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    
    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Metadata
    lead_source: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_name(self) -> str:
        """Full name."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else "Unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            "title": self.title,
            "department": self.department,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            "lead_source": self.lead_source,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "custom_fields": self.custom_fields
        }


@dataclass
class CRMDeal:
    """CRM Deal/Opportunity model."""
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Financial
    amount: float = 0.0
    currency: str = "VND"
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    
    # Deal info
    stage: str = "prospecting"
    probability: float = 0.0
    expected_close_date: Optional[datetime] = None
    actual_close_date: Optional[datetime] = None
    
    # Links
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    
    # Metadata
    status: str = "open"
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "amount": self.amount,
            "currency": self.currency,
            "discount_percent": self.discount_percent,
            "discount_amount": self.discount_amount,
            "stage": self.stage,
            "probability": self.probability,
            "expected_close_date": self.expected_close_date.isoformat() if self.expected_close_date else None,
            "actual_close_date": self.actual_close_date.isoformat() if self.actual_close_date else None,
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "custom_fields": self.custom_fields
        }


@dataclass
class CRMCompany:
    """CRM Company/Account model."""
    id: Optional[str] = None
    name: Optional[str] = None
    legal_name: Optional[str] = None
    website: Optional[str] = None
    
    # Contact info
    email: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    
    # Address
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_country: Optional[str] = None
    
    # Company info
    industry: Optional[str] = None
    company_size: Optional[str] = None
    revenue: Optional[float] = None
    tax_id: Optional[str] = None
    
    # Metadata
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "fax": self.fax,
            "billing_address": self.billing_address,
            "billing_city": self.billing_city,
            "billing_state": self.billing_state,
            "billing_country": self.billing_country,
            "billing_postal_code": self.billing_postal_code,
            "industry": self.industry,
            "company_size": self.company_size,
            "revenue": self.revenue,
            "tax_id": self.tax_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "custom_fields": self.custom_fields
        }


@dataclass
class CRMTask:
    """CRM Task model."""
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Task info
    task_type: str = "follow_up"
    status: str = "pending"  # pending, in_progress, completed, cancelled
    priority: str = "medium"  # low, medium, high, urgent
    
    # Due date
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Links
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    
    # Reminder
    reminder_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "deal_id": self.deal_id,
            "company_id": self.company_id,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "reminder_at": self.reminder_at.isoformat() if self.reminder_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "custom_fields": self.custom_fields
        }


@dataclass
class CRMOpportunity:
    """
    CRM Opportunity model - extended version của Deal.
    Dùng cho sales pipeline management.
    """
    id: Optional[str] = None
    name: Optional[str] = None
    
    # Stage pipeline
    pipeline_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    stage_id: Optional[str] = None
    stage_name: Optional[str] = None
    stage_order: int = 0
    
    # Financial
    amount: float = 0.0
    currency: str = "VND"
    
    # Probability & dates
    probability: float = 0.0
    expected_close_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    
    # Links
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    
    # Activities
    activities_count: int = 0
    last_activity_date: Optional[datetime] = None
    
    # Metadata
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "pipeline_id": self.pipeline_id,
            "pipeline_name": self.pipeline_name,
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "stage_order": self.stage_order,
            "amount": self.amount,
            "currency": self.currency,
            "probability": self.probability,
            "expected_close_date": self.expected_close_date.isoformat() if self.expected_close_date else None,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "activities_count": self.activities_count,
            "last_activity_date": self.last_activity_date.isoformat() if self.last_activity_date else None,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "custom_fields": self.custom_fields
        }


# ============== Base Client ==============

class BaseCRMClient(ABC):
    """
    Abstract base class cho CRM clients.
    Implement class này để tạo CRM client mới.
    """
    
    def __init__(self, config: CRMConfig):
        """
        Khởi tạo CRM client.
        
        Args:
            config: CRM configuration
        """
        self.config = config
        self._http_client = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Kết nối tới CRM.
        
        Returns:
            True nếu thành công
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Ngắt kết nối."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test kết nối.
        
        Returns:
            Dict với thông tin connection test
        """
        pass
    
    # === Contact Operations ===
    
    @abstractmethod
    async def get_contact(self, contact_id: str) -> Optional[CRMContact]:
        """
        Lấy contact theo ID.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            CRMContact hoặc None
        """
        pass
    
    @abstractmethod
    async def search_contacts(
        self,
        query: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        limit: int = 20
    ) -> List[CRMContact]:
        """
        Tìm kiếm contacts.
        
        Args:
            query: Search query
            email: Filter by email
            phone: Filter by phone
            limit: Max results
            
        Returns:
            List of CRMContact
        """
        pass
    
    @abstractmethod
    async def create_contact(self, contact: CRMContact) -> CRMContact:
        """
        Tạo contact mới.
        
        Args:
            contact: Contact data
            
        Returns:
            Created contact với ID
        """
        pass
    
    @abstractmethod
    async def update_contact(self, contact: CRMContact) -> CRMContact:
        """
        Update contact.
        
        Args:
            contact: Contact data with ID
            
        Returns:
            Updated contact
        """
        pass
    
    @abstractmethod
    async def delete_contact(self, contact_id: str) -> bool:
        """
        Xóa contact.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            True nếu thành công
        """
        pass
    
    # === Deal Operations ===
    
    @abstractmethod
    async def get_deal(self, deal_id: str) -> Optional[CRMDeal]:
        """Lấy deal theo ID."""
        pass
    
    @abstractmethod
    async def search_deals(
        self,
        query: Optional[str] = None,
        stage: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 20
    ) -> List[CRMDeal]:
        """Tìm kiếm deals."""
        pass
    
    @abstractmethod
    async def create_deal(self, deal: CRMDeal) -> CRMDeal:
        """Tạo deal mới."""
        pass
    
    @abstractmethod
    async def update_deal(self, deal: CRMDeal) -> CRMDeal:
        """Update deal."""
        pass
    
    @abstractmethod
    async def delete_deal(self, deal_id: str) -> bool:
        """Xóa deal."""
        pass
    
    # === Company Operations ===
    
    @abstractmethod
    async def get_company(self, company_id: str) -> Optional[CRMCompany]:
        """Lấy company theo ID."""
        pass
    
    @abstractmethod
    async def search_companies(
        self,
        query: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 20
    ) -> List[CRMCompany]:
        """Tìm kiếm companies."""
        pass
    
    @abstractmethod
    async def create_company(self, company: CRMCompany) -> CRMCompany:
        """Tạo company mới."""
        pass
    
    @abstractmethod
    async def update_company(self, company: CRMCompany) -> CRMCompany:
        """Update company."""
        pass
    
    # === Task Operations ===
    
    @abstractmethod
    async def get_tasks(
        self,
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[CRMTask]:
        """Lấy tasks."""
        pass
    
    @abstractmethod
    async def create_task(self, task: CRMTask) -> CRMTask:
        """Tạo task mới."""
        pass
    
    @abstractmethod
    async def update_task(self, task: CRMTask) -> CRMTask:
        """Update task."""
        pass
    
    @abstractmethod
    async def complete_task(self, task_id: str) -> bool:
        """Đánh dấu task hoàn thành."""
        pass
    
    # === Dashboard & Reports ===
    
    @abstractmethod
    async def get_sales_pipeline(self, pipeline_id: Optional[str] = None) -> List[CRMOpportunity]:
        """
        Lấy sales pipeline.
        
        Args:
            pipeline_id: Pipeline ID (optional)
            
        Returns:
            List of opportunities in pipeline
        """
        pass
    
    @abstractmethod
    async def get_sales_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy sales summary.
        
        Args:
            start_date: Start date
            end_date: End date
            owner_id: Filter by owner
            
        Returns:
            Summary dict
        """
        pass
    
    # === Utility Methods ===
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime từ various formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    def _format_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Format datetime sang ISO string."""
        if dt is None:
            return None
        return dt.isoformat()
