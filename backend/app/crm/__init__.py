"""
CRM Integration Module - Tích hợp với CRM systems.
Hỗ trợ nhiều CRM providers (Salesforce, HubSpot, v.v.).
"""
from .base import (
    BaseCRMClient,
    CRMContact,
    CRMDeal,
    CRMCompany,
    CRMTask,
    CRMOpportunity,
    CRMConfig,
)
from .factory import CRMClientFactory

__all__ = [
    "BaseCRMClient",
    "CRMContact",
    "CRMDeal", 
    "CRMCompany",
    "CRMTask",
    "CRMOpportunity",
    "CRMConfig",
    "CRMClientFactory",
]
