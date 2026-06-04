"""Validation-related data models."""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """SHACL violation severity levels."""
    VIOLATION = "Violation"
    WARNING = "Warning"
    INFO = "Info"


class ViolationEntry(BaseModel):
    """Single SHACL validation violation."""
    
    focus_node: str = Field(..., description="IRI of the focus node")
    result_path: Optional[str] = Field(None, description="Property path that failed")
    value: Optional[Any] = Field(None, description="Value that violated constraint")
    message: str = Field(..., description="Human-readable violation message")
    severity: Severity = Severity.VIOLATION
    source_constraint: Optional[str] = Field(None, description="SHACL constraint IRI")
    source_shape: Optional[str] = Field(None, description="SHACL shape IRI")


class ValidationReport(BaseModel):
    """SHACL validation report."""
    
    conforms: bool = Field(..., description="True if data conforms to shapes")
    violations: List[ViolationEntry] = Field(default_factory=list)
    warnings: List[ViolationEntry] = Field(default_factory=list)
    infos: List[ViolationEntry] = Field(default_factory=list)
    total_violations: int = 0
    total_warnings: int = 0
    total_infos: int = 0
    validated_at: Optional[str] = None
    
    def __init__(self, **data: Any):
        super().__init__(**data)
        self.total_violations = len([v for v in self.violations if v.severity == Severity.VIOLATION])
        self.total_warnings = len([v for v in self.violations if v.severity == Severity.WARNING])
        self.total_infos = len([v for v in self.violations if v.severity == Severity.INFO])
