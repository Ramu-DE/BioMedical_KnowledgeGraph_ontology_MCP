"""Graph Sync MCP Server for bidirectional Neo4j ↔ Neptune synchronization."""

from datetime import datetime
from typing import Any, Dict, Optional

from biomedical_kg_mcp.config.settings import Neo4jAuraSettings
from biomedical_kg_mcp.mcp_servers.base import BaseMCPServer, ToolDefinition
from biomedical_kg_mcp.services.graph_sync_orchestrator import SyncOrchestrator
from biomedical_kg_mcp.services.iri_minter import IRIMinter
from biomedical_kg_mcp.services.neo4j_client import Neo4jClient
from biomedical_kg_mcp.services.shacl_validator import SHACLValidator
from biomedical_kg_mcp.services.cache_service import CacheService


class GraphSyncMCPServer(BaseMCPServer):
    """
    Graph Sync MCP Server for bidirectional synchronization.
    
    Provides tools for:
    - Syncing Neo4j → Neptune with validation
    - Syncing Neptune → Neo4j
    - Validating data before sync
    - Checking sync job status
    - Listing and resolving conflicts
    """
    
    def __init__(
        self,
        neo4j_settings: Neo4jAuraSettings,
        iri_minter: IRIMinter,
        shacl_validator: SHACLValidator,
        cache_service: Optional[CacheService] = None
    ):
        """Initialize Graph Sync MCP Server."""
        super().__init__("graph-sync-server", "1.0.0")
        
        # Initialize clients
        neo4j_client = Neo4jClient(
            uri=neo4j_settings.uri,
            user=neo4j_settings.user,
            password=neo4j_settings.password,
            database=neo4j_settings.database
        )
        
        # Initialize orchestrator
        self.orchestrator = SyncOrchestrator(
            neo4j_client=neo4j_client,
            iri_minter=iri_minter,
            shacl_validator=shacl_validator
        )
        self.cache = cache_service
        
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all sync tools."""
        
        # Tool 1: sync_to_neptune
        self.register_tool(ToolDefinition(
            name="sync_to_neptune",
            description="Sync data from Neo4j to Neptune with validation",
            input_schema={
                "type": "object",
                "properties": {
                    "cypher_query": {
                        "type": "string",
                        "description": "Cypher query to extract subgraph from Neo4j"
                    },
                    "named_graph": {
                        "type": "string",
                        "description": "Target Neptune named graph URI"
                    },
                    "validate": {
                        "type": "boolean",
                        "description": "Enable SHACL validation (default: true)"
                    }
                },
                "required": ["cypher_query", "named_graph"]
            }
        ))
        
        # Tool 2: sync_from_neptune
        self.register_tool(ToolDefinition(
            name="sync_from_neptune",
            description="Sync data from Neptune to Neo4j",
            input_schema={
                "type": "object",
                "properties": {
                    "sparql_construct": {
                        "type": "string",
                        "description": "SPARQL CONSTRUCT query to extract RDF from Neptune"
                    },
                    "target_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Target node labels in Neo4j"
                    }
                },
                "required": ["sparql_construct", "target_labels"]
            }
        ))
        
        # Tool 3: sync_validate
        self.register_tool(ToolDefinition(
            name="sync_validate",
            description="Validate data without performing sync",
            input_schema={
                "type": "object",
                "properties": {
                    "cypher_query": {
                        "type": "string",
                        "description": "Cypher query to extract data for validation"
                    }
                },
                "required": ["cypher_query"]
            }
        ))
        
        # Tool 4: sync_status
        self.register_tool(ToolDefinition(
            name="sync_status",
            description="Get sync job status",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Sync job ID"
                    }
                },
                "required": []
            }
        ))
        
        # Tool 5: sync_conflicts
        self.register_tool(ToolDefinition(
            name="sync_conflicts",
            description="List synchronization conflicts",
            input_schema={
                "type": "object",
                "properties": {
                    "since": {
                        "type": "string",
                        "description": "ISO timestamp - conflicts since this time"
                    },
                    "resolved": {
                        "type": "boolean",
                        "description": "Filter by resolution status"
                    }
                },
                "required": []
            }
        ))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool by name."""
        
        if tool_name == "sync_to_neptune":
            return await self._tool_sync_to_neptune(arguments)
        elif tool_name == "sync_from_neptune":
            return await self._tool_sync_from_neptune(arguments)
        elif tool_name == "sync_validate":
            return await self._tool_sync_validate(arguments)
        elif tool_name == "sync_status":
            return await self._tool_sync_status(arguments)
        elif tool_name == "sync_conflicts":
            return await self._tool_sync_conflicts(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _tool_sync_to_neptune(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sync from Neo4j to Neptune with cache invalidation."""
        cypher_query = args["cypher_query"]
        named_graph = args["named_graph"]
        validate = args.get("validate", True)
        
        job = await self.orchestrator.sync_to_neptune(
            cypher_query=cypher_query,
            named_graph=named_graph,
            validate=validate
        )
        
        # Invalidate cache for synced entities
        if self.cache and job.entity_ids:
            invalidated = await self.cache.invalidate_entities(job.entity_ids)
            print(f"Cache invalidated: {invalidated} entries for {len(job.entity_ids)} entities")
        
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "entity_count": job.entity_count,
            "triple_count": job.triple_count,
            "error_message": job.error_message
        }
    
    async def _tool_sync_from_neptune(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sync from Neptune to Neo4j with cache invalidation."""
        sparql_construct = args["sparql_construct"]
        target_labels = args["target_labels"]
        
        job = await self.orchestrator.sync_from_neptune(
            sparql_construct=sparql_construct,
            target_labels=target_labels
        )
        
        # Invalidate cache for synced entities
        if self.cache and job.entity_ids:
            invalidated = await self.cache.invalidate_entities(job.entity_ids)
            print(f"Cache invalidated: {invalidated} entries for {len(job.entity_ids)} entities")
        
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "entity_count": job.entity_count,
            "error_message": job.error_message
        }
    
    async def _tool_sync_validate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data without syncing."""
        cypher_query = args["cypher_query"]
        
        # Perform validation only (no actual sync)
        job = await self.orchestrator.sync_to_neptune(
            cypher_query=cypher_query,
            named_graph="",
            validate=True
        )
        
        return {
            "valid": job.status.value != "failed",
            "error_message": job.error_message
        }
    
    async def _tool_sync_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get sync job status."""
        job_id = args.get("job_id")
        
        if job_id:
            job = self.orchestrator.get_job(job_id)
            if job:
                return {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "direction": job.direction.value,
                    "entity_count": job.entity_count,
                    "triple_count": job.triple_count,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message
                }
            else:
                return {"error": "Job not found"}
        else:
            # Return all jobs
            return {"error": "job_id parameter required"}
    
    async def _tool_sync_conflicts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List synchronization conflicts."""
        since_str = args.get("since")
        resolved = args.get("resolved")
        
        since = datetime.fromisoformat(since_str) if since_str else None
        
        conflicts = self.orchestrator.list_conflicts(since=since, resolved=resolved)
        
        return {
            "conflicts": [
                {
                    "conflict_id": c.conflict_id,
                    "entity_id": c.entity_id,
                    "entity_type": c.entity_type,
                    "resolution": c.resolution.value,
                    "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None
                }
                for c in conflicts
            ],
            "count": len(conflicts)
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities."""
        return {
            "tools": True,
            "sync_directions": ["to_neptune", "from_neptune"],
            "validation": "SHACL",
            "conflict_resolution": "last-writer-wins"
        }
