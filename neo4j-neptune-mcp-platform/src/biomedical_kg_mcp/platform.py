"""
Neo4j-Neptune MCP Platform

Unified entry point for all MCP servers with integrated security and caching.
"""

from typing import Optional
from redis.asyncio import Redis

from biomedical_kg_mcp.config.settings import PlatformSettings
from biomedical_kg_mcp.mcp_servers.neo4j_aura_server import Neo4jAuraMCPServer
from biomedical_kg_mcp.mcp_servers.neptune_server import NeptuneMCPServer
from biomedical_kg_mcp.mcp_servers.graph_sync_server import GraphSyncMCPServer
from biomedical_kg_mcp.mcp_servers.lakehouse_server import LakehouseMCPServer

from biomedical_kg_mcp.services.cache_service import CacheService
from biomedical_kg_mcp.services.auth_service import AuthService
from biomedical_kg_mcp.services.rate_limiter import RateLimiter
from biomedical_kg_mcp.services.audit_logger import AuditLogger
from biomedical_kg_mcp.services.iri_minter import IRIMinter
from biomedical_kg_mcp.services.shacl_validator import SHACLValidator
from biomedical_kg_mcp.services.llm_service import LLMService
from biomedical_kg_mcp.services.ontology_manager import OntologyManager


class MCPPlatform:
    """Unified MCP platform with all servers and services."""

    def __init__(self, settings: Optional[PlatformSettings] = None):
        """Initialize platform with all services."""
        self.settings = settings or PlatformSettings()
        
        # Initialize shared services
        self._init_shared_services()
        
        # Initialize MCP servers
        self._init_servers()

    def _init_shared_services(self):
        """Initialize shared services."""
        # Redis client
        self.redis = Redis.from_url(self.settings.redis.url)
        
        # Cache service
        self.cache = CacheService(self.redis)
        
        # Security services
        self.auth = AuthService()
        self.rate_limiter = RateLimiter(self.redis)
        self.audit_logger = AuditLogger()
        
        # Core services
        self.iri_minter = IRIMinter()
        self.shacl_validator = SHACLValidator()
        self.llm_service = LLMService(self.settings.llm)
        self.ontology_manager = OntologyManager()

    def _init_servers(self):
        """Initialize all MCP servers."""
        # Neo4j Aura Server
        self.neo4j_server = Neo4jAuraMCPServer(
            settings=self.settings.neo4j_aura,
            cache_service=self.cache
        )
        
        # Neptune Server
        self.neptune_server = NeptuneMCPServer(
            settings=self.settings.neptune,
            cache_service=self.cache
        )
        
        # Graph Sync Server
        self.graph_sync_server = GraphSyncMCPServer(
            neo4j_settings=self.settings.neo4j_aura,
            iri_minter=self.iri_minter,
            shacl_validator=self.shacl_validator,
            cache_service=self.cache
        )
        
        # Lakehouse Server
        self.lakehouse_server = LakehouseMCPServer(
            settings=self.settings.databricks,
            iri_minter=self.iri_minter,
            shacl_validator=self.shacl_validator,
            llm_service=self.llm_service
        )

    async def handle_request(self, request: dict) -> dict:
        """
        Handle MCP request with security and routing.
        
        Args:
            request: JSON-RPC 2.0 request
            
        Returns:
            JSON-RPC 2.0 response
        """
        # Extract API key
        api_key = request.get("headers", {}).get("X-API-Key")
        
        # Authenticate
        key_info = self.auth.validate_key(api_key)
        if not key_info:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid API key"},
                "id": request.get("id")
            }
        
        # Check rate limit
        allowed, count, limit = await self.rate_limiter.check_rate_limit(
            key_info.key_id, key_info.tier
        )
        if not allowed:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": f"Rate limit exceeded: {count}/{limit}"},
                "id": request.get("id")
            }
        
        # Route to appropriate server
        method = request.get("method", "")
        server = self._route_request(method)
        
        if not server:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": request.get("id")
            }
        
        # Authorize tool
        if not self.auth.authorize_tool(key_info, method):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Unauthorized"},
                "id": request.get("id")
            }
        
        # Start audit
        audit_ctx = self.audit_logger.start_invocation(
            method, key_info.key_id, request.get("params", {})
        )
        
        # Execute tool
        try:
            result = await server.call_tool(method, request.get("params", {}))
            self.audit_logger.end_invocation(audit_ctx, "success")
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request.get("id")
            }
        except Exception as e:
            self.audit_logger.end_invocation(audit_ctx, "failed", str(e))
            
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request.get("id")
            }

    def _route_request(self, method: str):
        """Route request to appropriate server."""
        if method.startswith("neo4j_"):
            return self.neo4j_server
        elif method.startswith("neptune_"):
            return self.neptune_server
        elif method.startswith("sync_"):
            return self.graph_sync_server
        elif method.startswith("lakehouse_"):
            return self.lakehouse_server
        return None

    async def close(self):
        """Cleanup resources."""
        await self.redis.close()
        await self.neo4j_server.client.close()
        await self.neptune_server.client.aclose()
