"""Neptune MCP Server with SPARQL, openCypher, and bulk loading."""

import asyncio
from typing import Any, Dict, Optional

import httpx

from biomedical_kg_mcp.config.settings import NeptuneSettings
from biomedical_kg_mcp.mcp_servers.base import BaseMCPServer, ToolDefinition
from biomedical_kg_mcp.services.sigv4_auth import SigV4Authenticator
from biomedical_kg_mcp.services.cache_service import CacheService


class NeptuneMCPServer(BaseMCPServer):
    """
    Neptune MCP Server for production RDF and property graph operations.
    
    Provides 5 tools:
    - neptune_sparql: Execute SPARQL 1.1 queries
    - neptune_cypher: Execute openCypher queries
    - neptune_bulk_load: Initiate bulk loader from S3
    - neptune_load_status: Check bulk load job status
    - neptune_status: Get cluster status
    """
    
    def __init__(self, settings: NeptuneSettings, cache_service: Optional[CacheService] = None):
        """Initialize Neptune MCP Server."""
        super().__init__("neptune-server", "1.0.0")
        
        self.settings = settings
        self.base_url = f"https://{settings.cluster_endpoint}:{settings.port}"
        self.authenticator = SigV4Authenticator(region=settings.region)
        self.client = httpx.AsyncClient(timeout=30.0)
        self.max_retries = 3
        self.cache = cache_service
        
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all Neptune tools."""
        
        # Tool 1: neptune_sparql
        self.register_tool(ToolDefinition(
            name="neptune_sparql",
            description="Execute SPARQL 1.1 query against Neptune",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SPARQL query"
                    },
                    "named_graph": {
                        "type": "string",
                        "description": "Named graph URI (optional)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Query timeout in seconds (default: 30)"
                    }
                },
                "required": ["query"]
            }
        ))
        
        # Tool 2: neptune_cypher
        self.register_tool(ToolDefinition(
            name="neptune_cypher",
            description="Execute openCypher query against Neptune",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "openCypher query"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters"
                    }
                },
                "required": ["query"]
            }
        ))
        
        # Tool 3: neptune_bulk_load
        self.register_tool(ToolDefinition(
            name="neptune_bulk_load",
            description="Initiate Neptune bulk loader from S3",
            input_schema={
                "type": "object",
                "properties": {
                    "s3_uri": {
                        "type": "string",
                        "description": "S3 URI (s3://bucket/key)"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["ntriples", "turtle", "rdfxml"],
                        "description": "RDF format"
                    },
                    "named_graph": {
                        "type": "string",
                        "description": "Target named graph URI"
                    }
                },
                "required": ["s3_uri", "format"]
            }
        ))
        
        # Tool 4: neptune_load_status
        self.register_tool(ToolDefinition(
            name="neptune_load_status",
            description="Check Neptune bulk load job status",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Bulk load job ID"
                    }
                },
                "required": ["job_id"]
            }
        ))
        
        # Tool 5: neptune_status
        self.register_tool(ToolDefinition(
            name="neptune_status",
            description="Get Neptune cluster status",
            input_schema={
                "type": "object",
                "properties": {}
            }
        ))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool by name."""
        
        if tool_name == "neptune_sparql":
            return await self._tool_sparql(arguments)
        elif tool_name == "neptune_cypher":
            return await self._tool_cypher(arguments)
        elif tool_name == "neptune_bulk_load":
            return await self._tool_bulk_load(arguments)
        elif tool_name == "neptune_load_status":
            return await self._tool_load_status(arguments)
        elif tool_name == "neptune_status":
            return await self._tool_status(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _tool_sparql(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SPARQL query with caching."""
        query = args["query"]
        named_graph = args.get("named_graph")
        
        # Check cache
        cache_params = {"named_graph": named_graph} if named_graph else None
        if self.cache:
            cached = await self.cache.get_query_result(
                scope="neptune_sparql",
                query=query,
                params=cache_params
            )
            if cached:
                return cached
        
        url = f"{self.base_url}/sparql"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        # Add named graph if specified
        if named_graph:
            query = f"FROM <{named_graph}> {query}"
        
        body = f"query={query}"
        
        response = await self._signed_request("POST", url, headers, body)
        
        result_data = {
            "results": response.get("results", {}).get("bindings", []),
            "count": len(response.get("results", {}).get("bindings", []))
        }
        
        # Extract entity IRIs for cache invalidation
        entity_ids = self._extract_sparql_entities(result_data["results"])
        
        # Cache with entity tracking
        if self.cache:
            await self.cache.set_query_result(
                scope="neptune_sparql",
                query=query,
                params=cache_params,
                result=result_data,
                entity_ids=entity_ids
            )
        
        return result_data
    
    def _extract_sparql_entities(self, bindings: list) -> list:
        """Extract entity IRIs from SPARQL results."""
        entity_ids = []
        for binding in bindings:
            for var, value in binding.items():
                if value.get("type") == "uri":
                    # Extract last part of IRI as ID
                    iri = value.get("value", "")
                    entity_id = iri.split("/")[-1] if "/" in iri else iri
                    if entity_id:
                        entity_ids.append(entity_id)
        return list(set(entity_ids))
    
    async def _tool_cypher(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute openCypher query."""
        query = args["query"]
        parameters = args.get("parameters", {})
        
        url = f"{self.base_url}/opencypher"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = f"query={query}"
        
        response = await self._signed_request("POST", url, headers, body)
        
        return {
            "results": response.get("results", []),
            "count": len(response.get("results", []))
        }
    
    async def _tool_bulk_load(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate bulk load from S3."""
        s3_uri = args["s3_uri"]
        format_type = args["format"]
        named_graph = args.get("named_graph", "")
        
        url = f"{self.base_url}/loader"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "source": s3_uri,
            "format": format_type,
            "iamRoleArn": self.settings.iam_role_arn,
            "region": self.settings.region,
            "failOnError": "FALSE",
            "parallelism": "MEDIUM"
        }
        
        if named_graph:
            payload["parserConfiguration"] = {"namedGraphUri": named_graph}
        
        import json
        body = json.dumps(payload)
        
        response = await self._signed_request("POST", url, headers, body)
        
        return {
            "job_id": response.get("payload", {}).get("loadId"),
            "status": response.get("status")
        }
    
    async def _tool_load_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check bulk load status."""
        job_id = args["job_id"]
        
        url = f"{self.base_url}/loader/{job_id}"
        headers = {}
        
        response = await self._signed_request("GET", url, headers)
        
        payload = response.get("payload", {})
        return {
            "job_id": job_id,
            "status": payload.get("overallStatus", {}).get("status"),
            "records_loaded": payload.get("overallStatus", {}).get("totalRecords", 0),
            "errors": payload.get("overallStatus", {}).get("errors", [])
        }
    
    async def _tool_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get cluster status."""
        url = f"{self.base_url}/status"
        headers = {}
        
        response = await self._signed_request("GET", url, headers)
        
        return {
            "status": response.get("status"),
            "version": response.get("version"),
            "dbEngineVersion": response.get("dbEngineVersion")
        }
    
    async def _signed_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: str = ""
    ) -> Dict[str, Any]:
        """Make signed HTTP request with retry."""
        for attempt in range(self.max_retries):
            try:
                # Sign request
                signed_headers = self.authenticator.sign_request(
                    method, url, headers, body
                )
                
                # Make request
                response = await self.client.request(
                    method,
                    url,
                    headers=signed_headers,
                    content=body
                )
                
                # Handle throttling
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # 1s, 2s, 4s
                        await asyncio.sleep(wait_time)
                        continue
                
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    raise
        
        return {}
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities."""
        return {
            "tools": True,
            "graph_database": "AWS Neptune",
            "query_languages": ["SPARQL", "openCypher"],
            "authentication": "AWS IAM SigV4"
        }
    
    async def stop(self) -> None:
        """Stop server and close connections."""
        await self.client.aclose()
