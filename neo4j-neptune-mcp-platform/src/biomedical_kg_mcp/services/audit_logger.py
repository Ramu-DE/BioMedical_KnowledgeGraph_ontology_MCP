"""
Audit Logging Service

Logs all tool invocations with timing and status information.
"""

import time
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class AuditEntry(BaseModel):
    """Audit log entry."""
    timestamp: datetime
    tool_name: str
    caller_identity: str
    duration_ms: int
    status: str  # "success" or "failed"
    error_message: Optional[str] = None
    arguments: Optional[dict] = None


class AuditLogger:
    """Audit logging for tool invocations."""

    def __init__(self):
        self.entries: list[AuditEntry] = []
        self.max_entries = 10000  # Keep last 10k entries in memory

    def start_invocation(self, tool_name: str, caller_identity: str, arguments: dict) -> dict:
        """
        Start tracking tool invocation.
        
        Args:
            tool_name: Tool being invoked
            caller_identity: API key ID
            arguments: Tool arguments
            
        Returns:
            Context dict with start time
        """
        return {
            "tool_name": tool_name,
            "caller_identity": caller_identity,
            "arguments": arguments,
            "start_time": time.time(),
        }

    def end_invocation(
        self,
        context: dict,
        status: str,
        error_message: Optional[str] = None
    ) -> AuditEntry:
        """
        End tracking and log entry.
        
        Args:
            context: Context from start_invocation
            status: "success" or "failed"
            error_message: Error message if failed
            
        Returns:
            Audit entry
        """
        duration_ms = int((time.time() - context["start_time"]) * 1000)
        
        entry = AuditEntry(
            timestamp=datetime.now(),
            tool_name=context["tool_name"],
            caller_identity=context["caller_identity"],
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            arguments=context.get("arguments"),
        )
        
        self.entries.append(entry)
        
        # Trim to max size
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        
        return entry

    def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        """Get recent audit entries."""
        return self.entries[-limit:]

    def get_by_caller(self, caller_identity: str, limit: int = 100) -> list[AuditEntry]:
        """Get entries by caller."""
        matching = [e for e in self.entries if e.caller_identity == caller_identity]
        return matching[-limit:]

    def get_failed(self, limit: int = 100) -> list[AuditEntry]:
        """Get failed invocations."""
        failed = [e for e in self.entries if e.status == "failed"]
        return failed[-limit:]
