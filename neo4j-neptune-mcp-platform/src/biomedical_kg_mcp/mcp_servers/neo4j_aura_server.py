"""Neo4j Aura MCP Server with 5 tools for cloud LPG operations."""

from typing import Any, Dict, Optional

from biomedical_kg_mcp.config.settings import Neo4jAuraSettings
from biomedical_kg_mcp.mcp_servers.base import BaseMCPServer, ToolDefinition
from biomedical_kg_mcp.services.neo4j_client import Neo4jClient
from biomedical_kg_mcp.services.cache_service import CacheService


class Neo4jAuraMCPServer(BaseMCPServer):
    """
    Neo4j Aura MCP Server for cloud LPG query operations.
    
    Provides 5 tools:
    - neo4j_query: Execute Cypher queries
    - neo4j_pathfind: Find shortest paths
    - neo4j_community: Run community detection algorithms
    - neo4j_expand: Expand node neighborhoods
    - neo4j_schema: Get graph schema
    """
    
    def __init__(self, settings: Neo4jAuraSettings, cache_service: Optional[CacheService] = None):
        """Initialize Neo4j Aura MCP Server."""
        super().__init__("neo4j-aura-server", "1.0.0")
        
        self.client = Neo4jClient(
            uri=settings.uri,
            user=settings.user,
            password=settings.password,
            database=settings.database,
            max_connection_pool_size=settings.max_connection_pool_size,
            connection_timeout=settings.connection_timeout,
        )
        self.cache = cache_service
        
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all Neo4j Aura tools."""
        
        # Tool 1: neo4j_query
        self.register_tool(ToolDefinition(
            name="neo4j_query",
            description="Execute a Cypher query against Neo4j Aura",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Cypher query to execute"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Query timeout in seconds (default: 10)"
                    }
                },
                "required": ["query"]
            }
        ))
        
        # Tool 2: neo4j_pathfind
        self.register_tool(ToolDefinition(
            name="neo4j_pathfind",
            description="Find shortest path between two nodes",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source node ID"
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Target node ID"
                    },
                    "algorithm": {
                        "type": "string",
                        "enum": ["dijkstra", "bfs"],
                        "description": "Path-finding algorithm"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum path depth (default: 10)"
                    }
                },
                "required": ["source_id", "target_id"]
            }
        ))
        
        # Tool 3: neo4j_community
        self.register_tool(ToolDefinition(
            name="neo4j_community",
            description="Run community detection algorithm",
            input_schema={
                "type": "object",
                "properties": {
                    "algorithm": {
                        "type": "string",
                        "enum": ["louvain", "label_prop", "wcc"],
                        "description": "Community detection algorithm"
                    },
                    "node_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Node labels to include (optional)"
                    }
                },
                "required": ["algorithm"]
            }
        ))
        
        # Tool 4: neo4j_expand
        self.register_tool(ToolDefinition(
            name="neo4j_expand",
            description="Expand node neighborhood",
            input_schema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "Node ID to expand from"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Traversal depth (default: 1)"
                    },
                    "rel_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relationship types filter (optional)"
                    }
                },
                "required": ["node_id"]
            }
        ))
        
        # Tool 5: neo4j_schema
        self.register_tool(ToolDefinition(
            name="neo4j_schema",
            description="Get graph schema (labels, relationships, properties)",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool by name."""
        
        if tool_name == "neo4j_query":
            return await self._tool_query(arguments)
        elif tool_name == "neo4j_pathfind":
            return await self._tool_pathfind(arguments)
        elif tool_name == "neo4j_community":
            return await self._tool_community(arguments)
        elif tool_name == "neo4j_expand":
            return await self._tool_expand(arguments)
        elif tool_name == "neo4j_schema":
            return await self._tool_schema(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _tool_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Cypher query with caching."""
        query = args["query"]
        parameters = args.get("parameters", {})
        timeout = args.get("timeout")
        
        # Check cache
        if self.cache:
            cached = await self.cache.get_query_result(
                scope="neo4j_query",
                query=query,
                params=parameters
            )
            if cached:
                return cached
        
        # Execute query
        results = await self.client.execute_query(query, parameters, timeout)
        
        # Extract entity IDs from results
        entity_ids = self._extract_entity_ids(results)
        
        result_data = {
            "results": results,
            "count": len(results)
        }
        
        # Cache with entity tracking
        if self.cache:
            await self.cache.set_query_result(
                scope="neo4j_query",
                query=query,
                params=parameters,
                result=result_data,
                entity_ids=entity_ids
            )
        
        return result_data
    
    def _extract_entity_ids(self, results: list) -> list:
        """Extract entity IDs from query results for cache invalidation."""
        entity_ids = []
        for record in results:
            if isinstance(record, dict):
                # Look for 'id' field in result
                if "id" in record:
                    entity_ids.append(record["id"])
                # Check nested structures
                for value in record.values():
                    if isinstance(value, dict) and "id" in value:
                        entity_ids.append(value["id"])
        return list(set(entity_ids))  # Deduplicate
    
    async def _tool_pathfind(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find shortest path between nodes."""
        source_id = args["source_id"]
        target_id = args["target_id"]
        algorithm = args.get("algorithm", "bfs")
        max_depth = args.get("max_depth", 10)
        
        if algorithm == "dijkstra":
            query = f"""
            MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
            CALL gds.shortestPath.dijkstra.stream({{
                sourceNode: source,
                targetNode: target,
                relationshipWeightProperty: 'weight'
            }})
            YIELD path
            RETURN path
            LIMIT 1
            """
        else:  # bfs
            query = f"""
            MATCH path = shortestPath(
                (source {{id: $source_id}})-[*..{max_depth}]-(target {{id: $target_id}})
            )
            RETURN path, length(path) as pathLength
            """
        
        results = await self.client.execute_query(query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        return {
            "paths": results,
            "count": len(results)
        }
    
    async def _tool_community(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run community detection."""
        algorithm = args["algorithm"]
        node_labels = args.get("node_labels")
        
        label_filter = ""
        if node_labels:
            label_filter = f":{':'.join(node_labels)}"
        
        if algorithm == "louvain":
            query = f"""
            CALL gds.louvain.stream({{
                nodeLabels: {node_labels or ['*']},
                relationshipTypes: ['*']
            }})
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).id as nodeId, communityId
            LIMIT 1000
            """
        elif algorithm == "label_prop":
            query = f"""
            MATCH (n{label_filter})
            WITH collect(n) as nodes
            CALL gds.labelPropagation.stream({{nodeProjection: nodes}})
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).id as nodeId, communityId
            LIMIT 1000
            """
        else:  # wcc
            query = f"""
            MATCH (n{label_filter})
            WITH collect(n) as nodes
            CALL gds.wcc.stream({{nodeProjection: nodes}})
            YIELD nodeId, componentId
            RETURN gds.util.asNode(nodeId).id as nodeId, componentId as communityId
            LIMIT 1000
            """
        
        results = await self.client.execute_query(query)
        
        return {
            "communities": results,
            "count": len(results)
        }
    
    async def _tool_expand(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Expand node neighborhood."""
        node_id = args["node_id"]
        depth = args.get("depth", 1)
        rel_types = args.get("rel_types")
        
        rel_filter = ""
        if rel_types:
            rel_filter = f":{':'.join(rel_types)}"
        
        query = f"""
        MATCH (start {{id: $node_id}})-[r{rel_filter}*..{depth}]-(neighbor)
        RETURN start, r, neighbor
        LIMIT 100
        """
        
        results = await self.client.execute_query(query, {"node_id": node_id})
        
        return {
            "nodes": results,
            "count": len(results)
        }
    
    async def _tool_schema(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get graph schema."""
        schema = await self.client.get_schema()
        return schema
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities."""
        return {
            "tools": True,
            "graph_database": "Neo4j Aura",
            "query_language": "Cypher"
        }
    
    async def stop(self) -> None:
        """Stop server and close connections."""
        await self.client.close()
