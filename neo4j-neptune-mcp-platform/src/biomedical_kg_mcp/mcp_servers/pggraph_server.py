"""
pgGraph MCP Server for Supply/Quality Module

Provides graph queries over PostgreSQL Supply/Quality data using pgGraph extension.
"""

from typing import Any, Dict, Optional
from biomedical_kg_mcp.mcp_servers.base import BaseMCPServer, ToolDefinition
from biomedical_kg_mcp.services.pggraph_client import PgGraphClient


class PgGraphMCPServer(BaseMCPServer):
    """pgGraph MCP Server for Supply/Quality traceability."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ):
        super().__init__("pggraph-server", "1.0.0")
        
        self.client = PgGraphClient(host, port, database, user, password)
        self._register_tools()

    async def initialize(self):
        """Initialize database connection."""
        await self.client.connect()

    def _register_tools(self):
        """Register pgGraph tools."""
        
        # Tool 1: trace_quality_event
        self.register_tool(ToolDefinition(
            name="pggraph_trace_quality_event",
            description="Trace quality event back through batch → drug → manufacturing site",
            input_schema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Quality event ID"}
                },
                "required": ["event_id"]
            }
        ))
        
        # Tool 2: site_impact
        self.register_tool(ToolDefinition(
            name="pggraph_site_impact",
            description="Find all batches, quality events, and drugs impacted by a manufacturing site",
            input_schema={
                "type": "object",
                "properties": {
                    "site_id": {"type": "string", "description": "Manufacturing site ID"}
                },
                "required": ["site_id"]
            }
        ))
        
        # Tool 3: batch_lineage
        self.register_tool(ToolDefinition(
            name="pggraph_batch_lineage",
            description="Get full lineage of a drug batch (site, drug, quality events)",
            input_schema={
                "type": "object",
                "properties": {
                    "batch_id": {"type": "string", "description": "Drug batch ID"}
                },
                "required": ["batch_id"]
            }
        ))
        
        # Tool 4: supply_path
        self.register_tool(ToolDefinition(
            name="pggraph_supply_path",
            description="Find shortest path between any two Supply/Quality entities",
            input_schema={
                "type": "object",
                "properties": {
                    "source_table": {"type": "string", "description": "Source table name"},
                    "source_id": {"type": "string", "description": "Source entity ID"},
                    "target_table": {"type": "string", "description": "Target table name"},
                    "target_id": {"type": "string", "description": "Target entity ID"}
                },
                "required": ["source_table", "source_id", "target_table", "target_id"]
            }
        ))
        
        # Tool 5: pggraph_query
        self.register_tool(ToolDefinition(
            name="pggraph_query",
            description="Execute raw SQL with pgGraph graph functions",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query"},
                    "params": {"type": "array", "description": "Query parameters (optional)"}
                },
                "required": ["query"]
            }
        ))

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool."""
        
        if tool_name == "pggraph_trace_quality_event":
            return await self._tool_trace_quality_event(arguments)
        elif tool_name == "pggraph_site_impact":
            return await self._tool_site_impact(arguments)
        elif tool_name == "pggraph_batch_lineage":
            return await self._tool_batch_lineage(arguments)
        elif tool_name == "pggraph_supply_path":
            return await self._tool_supply_path(arguments)
        elif tool_name == "pggraph_query":
            return await self._tool_query(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _tool_trace_quality_event(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Trace quality event back to source."""
        event_id = args["event_id"]
        
        # Traverse from quality_event backwards
        chain = await self.client.traverse(
            start_id=event_id,
            table="quality_events",
            direction="incoming",
            max_depth=3
        )
        
        return {
            "event_id": event_id,
            "chain": chain,
            "chain_length": len(chain)
        }

    async def _tool_site_impact(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get downstream impact of manufacturing site."""
        site_id = args["site_id"]
        
        # Traverse from site forwards
        impact = await self.client.traverse(
            start_id=site_id,
            table="manufacturing_sites",
            direction="outgoing",
            max_depth=3
        )
        
        # Categorize by entity type
        batches = [e for e in impact if e.get("table") == "drug_batches"]
        events = [e for e in impact if e.get("table") == "quality_events"]
        drugs = [e for e in impact if e.get("table") == "drugs"]
        
        return {
            "site_id": site_id,
            "total_impacted": len(impact),
            "batches": len(batches),
            "quality_events": len(events),
            "drugs": len(drugs),
            "details": impact
        }

    async def _tool_batch_lineage(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get batch lineage."""
        batch_id = args["batch_id"]
        
        # Get subgraph around batch
        subgraph = await self.client.subgraph(
            table="drug_batches",
            entity_id=batch_id,
            depth=2
        )
        
        return {
            "batch_id": batch_id,
            "nodes": subgraph["nodes"],
            "edges": subgraph["edges"],
            "node_count": len(subgraph["nodes"]),
            "edge_count": len(subgraph["edges"])
        }

    async def _tool_supply_path(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find shortest path."""
        path = await self.client.shortest_path(
            source_table=args["source_table"],
            source_id=args["source_id"],
            target_table=args["target_table"],
            target_id=args["target_id"]
        )
        
        return {
            "path_found": path is not None,
            "path": path or [],
            "path_length": len(path) if path else 0
        }

    async def _tool_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute raw SQL."""
        query = args["query"]
        params = tuple(args.get("params", []))
        
        results = await self.client.execute_query(query, params)
        
        return {
            "results": results,
            "count": len(results)
        }

    async def close(self):
        """Cleanup."""
        await self.client.close()
