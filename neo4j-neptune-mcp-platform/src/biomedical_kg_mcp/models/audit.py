"""Audit-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditStatus(str, Enum):
    """Audit entry status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AuditEntry(BaseModel):
    """Audit log entry for tool invocations."""
    
    audit_id: str = Field(..., description="Unique audit entry identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_name: str = Field(..., description="Name of invoked tool")
    caller_identity: str = Field(..., description="API key or user identifier")
    caller_tier: Optional[str] = Field(None, description="Rate limit tier")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool input arguments")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    status: AuditStatus = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result_summary: Optional[Dict[str, Any]] = Field(None, description="Summary of result")
