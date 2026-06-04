"""
API Key Authentication Service

Validates API keys and enforces tier-based access control.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel


class APIKeyTier(str, Enum):
    """API key access tiers."""
    ADMIN = "admin"
    AI_AGENT = "ai-agent"
    READ_ONLY = "read-only"
    WRITE = "write"


class APIKeyInfo(BaseModel):
    """API key information."""
    key_id: str
    tier: APIKeyTier
    description: str
    active: bool = True


class AuthService:
    """API key authentication and authorization."""

    def __init__(self):
        # In production, load from database or secure config
        self.api_keys: dict[str, APIKeyInfo] = {
            # Example keys (should be loaded from secure storage)
            "admin_key_001": APIKeyInfo(
                key_id="admin_001",
                tier=APIKeyTier.ADMIN,
                description="Admin access",
            ),
            "agent_key_001": APIKeyInfo(
                key_id="agent_001",
                tier=APIKeyTier.AI_AGENT,
                description="AI agent access",
            ),
            "read_key_001": APIKeyInfo(
                key_id="read_001",
                tier=APIKeyTier.READ_ONLY,
                description="Read-only access",
            ),
            "write_key_001": APIKeyInfo(
                key_id="write_001",
                tier=APIKeyTier.WRITE,
                description="Write access",
            ),
        }

    def validate_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """
        Validate API key.
        
        Args:
            api_key: API key from X-API-Key header
            
        Returns:
            APIKeyInfo if valid, None otherwise
        """
        if not api_key:
            return None
        
        key_info = self.api_keys.get(api_key)
        if key_info and key_info.active:
            return key_info
        
        return None

    def authorize_tool(self, key_info: APIKeyInfo, tool_name: str) -> bool:
        """
        Check if API key tier is authorized for tool.
        
        Args:
            key_info: API key information
            tool_name: Tool name
            
        Returns:
            True if authorized
        """
        # Admin can access everything
        if key_info.tier == APIKeyTier.ADMIN:
            return True
        
        # Check tool permissions by tier
        if self._is_read_tool(tool_name):
            # All tiers can read
            return True
        
        if self._is_write_tool(tool_name):
            # Only admin, ai-agent, and write can write
            return key_info.tier in [APIKeyTier.ADMIN, APIKeyTier.AI_AGENT, APIKeyTier.WRITE]
        
        # Default: allow
        return True

    def _is_read_tool(self, tool_name: str) -> bool:
        """Check if tool is read-only."""
        read_tools = [
            "neo4j_query",
            "neo4j_schema",
            "neo4j_expand",
            "neptune_sparql",
            "neptune_status",
            "sync_status",
            "sync_conflicts",
            "lakehouse_status",
        ]
        return tool_name in read_tools

    def _is_write_tool(self, tool_name: str) -> bool:
        """Check if tool performs writes."""
        write_tools = [
            "sync_to_neptune",
            "sync_from_neptune",
            "neptune_bulk_load",
            "lakehouse_ingest_bronze",
            "lakehouse_process_silver",
            "lakehouse_transform_gold",
            "lakehouse_run_pipeline",
        ]
        return tool_name in write_tools
