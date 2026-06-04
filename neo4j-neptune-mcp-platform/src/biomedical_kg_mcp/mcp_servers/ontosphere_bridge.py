"""Ontosphere MCP Bridge Server.

Bridges the Ontosphere browser-based RDF editor with the Neo4j-Neptune MCP platform.
Exposes MCP tools for loading ontology modules, validating with OWL reasoning,
and syncing validated RDF to Neptune via Graph Sync Server.
"""

from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import Field
import logging

from ..services.ontosphere_client import OntosphereClient
from ..config.settings import settings

logger = logging.getLogger(__name__)


class OntosphereBridge:
    """MCP server bridging Ontosphere visual editor with Neptune production graph."""
    
    def __init__(self, ontosphere_url: str = "https://thhanke.github.io/ontosphere/"):
        self.ontosphere_url = ontosphere_url
        self.client = OntosphereClient(ontosphere_url)
        self.server = Server("ontosphere-bridge")
        self._register_tools()
        
        # 7 OWL ontology modules
        self.modules = {
            "foundation": "https://biomedkg.org/ontology/foundation.ttl",
            "commercial": "https://biomedkg.org/ontology/commercial.ttl",
            "clinical": "https://biomedkg.org/ontology/clinical.ttl",
            "medical_affairs": "https://biomedkg.org/ontology/medical-affairs.ttl",
            "patient": "https://biomedkg.org/ontology/patient.ttl",
            "supply_quality": "https://biomedkg.org/ontology/supply-quality.ttl",
            "governance": "https://biomedkg.org/ontology/governance.ttl"
        }
    
    def _register_tools(self):
        """Register MCP tools for Ontosphere integration."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="ontosphere_load_module",
                    description="Load one of the 7 OWL ontology modules into Ontosphere browser editor",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "module": {
                                "type": "string",
                                "enum": ["foundation", "commercial", "clinical", "medical_affairs", 
                                        "patient", "supply_quality", "governance"],
                                "description": "Ontology module to load"
                            }
                        },
                        "required": ["module"]
                    }
                ),
                Tool(
                    name="ontosphere_load_all_modules",
                    description="Load all 7 ontology modules into Ontosphere",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="ontosphere_validate",
                    description="Run OWL 2 DL reasoning and SHACL validation in Ontosphere",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="ontosphere_export_rdf",
                    description="Export validated RDF from Ontosphere in Turtle format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["turtle", "rdfxml", "jsonld"],
                                "default": "turtle"
                            }
                        }
                    }
                ),
                Tool(
                    name="ontosphere_sync_to_neptune",
                    description="Validate in Ontosphere then sync to Neptune via Graph Sync Server",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="ontosphere_generate_url",
                    description="Generate Ontosphere startup URL with pre-loaded modules",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "modules": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of module names to pre-load"
                            },
                            "rdf_url": {
                                "type": "string",
                                "description": "Optional RDF data URL to load on startup"
                            }
                        }
                    }
                ),
                Tool(
                    name="ontosphere_query_sparql",
                    description="Query loaded RDF in Ontosphere via SPARQL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SPARQL query string"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            if name == "ontosphere_load_module":
                return await self._load_module(arguments["module"])
            elif name == "ontosphere_load_all_modules":
                return await self._load_all_modules()
            elif name == "ontosphere_validate":
                return await self._validate()
            elif name == "ontosphere_export_rdf":
                return await self._export_rdf(arguments.get("format", "turtle"))
            elif name == "ontosphere_sync_to_neptune":
                return await self._sync_to_neptune()
            elif name == "ontosphere_generate_url":
                return await self._generate_url(
                    arguments.get("modules", []),
                    arguments.get("rdf_url")
                )
            elif name == "ontosphere_query_sparql":
                return await self._query_sparql(arguments["query"])
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _load_module(self, module: str) -> List[TextContent]:
        """Load single ontology module into Ontosphere."""
        if module not in self.modules:
            return [TextContent(type="text", text=f"Unknown module: {module}")]
        
        url = self.modules[module]
        result = await self.client.load_ontology(url)
        
        return [TextContent(
            type="text",
            text=f"Loaded {module} module into Ontosphere\nURL: {url}\nTriples: {result.get('triple_count', 0)}"
        )]
    
    async def _load_all_modules(self) -> List[TextContent]:
        """Load all 7 ontology modules."""
        results = []
        for module, url in self.modules.items():
            result = await self.client.load_ontology(url)
            results.append(f"{module}: {result.get('triple_count', 0)} triples")
        
        return [TextContent(
            type="text",
            text=f"Loaded all 7 modules:\n" + "\n".join(results)
        )]
    
    async def _validate(self) -> List[TextContent]:
        """Run OWL reasoning and validation."""
        result = await self.client.run_reasoning()
        
        inferred = result.get("inferred_triples", 0)
        status = result.get("status", "unknown")
        
        return [TextContent(
            type="text",
            text=f"Validation complete\nStatus: {status}\nInferred triples: {inferred}"
        )]
    
    async def _export_rdf(self, format: str) -> List[TextContent]:
        """Export RDF from Ontosphere."""
        result = await self.client.export_graph(format)
        
        return [TextContent(
            type="text",
            text=f"Exported RDF ({format}):\n\n{result.get('data', '')}"
        )]
    
    async def _sync_to_neptune(self) -> List[TextContent]:
        """Validate and sync to Neptune."""
        # Run validation first
        validation = await self.client.run_reasoning()
        if validation.get("status") != "valid":
            return [TextContent(
                type="text",
                text=f"Validation failed: {validation.get('errors', [])}"
            )]
        
        # Export validated RDF
        export = await self.client.export_graph("turtle")
        rdf_data = export.get("data", "")
        
        # TODO: Send to Graph Sync Server for Neptune sync
        # This would integrate with your existing graph_sync_server.py
        
        return [TextContent(
            type="text",
            text=f"Validated and ready for Neptune sync\nTriples: {len(rdf_data.splitlines())}"
        )]
    
    async def _generate_url(
        self, 
        modules: List[str], 
        rdf_url: Optional[str] = None
    ) -> List[TextContent]:
        """Generate Ontosphere startup URL."""
        from urllib.parse import urlencode
        
        params = {}
        
        # Add ontology modules
        if modules:
            ontology_urls = [self.modules[m] for m in modules if m in self.modules]
            params["ontology"] = ",".join(ontology_urls)
        
        # Add RDF data URL
        if rdf_url:
            params["rdfUrl"] = rdf_url
        
        # Pre-load BFO and FOAF for biomedical context
        base_ontologies = ["bfo2020", "foaf"]
        params["ontologies"] = ",".join(base_ontologies)
        
        url = f"{self.ontosphere_url}?{urlencode(params)}"
        
        return [TextContent(
            type="text",
            text=f"Ontosphere URL:\n{url}\n\nModules: {', '.join(modules)}"
        )]
    
    async def _query_sparql(self, query: str) -> List[TextContent]:
        """Query Ontosphere graph via SPARQL."""
        result = await self.client.query_graph(query)
        
        return [TextContent(
            type="text",
            text=f"SPARQL Results:\n{result}"
        )]
    
    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Entry point for Ontosphere Bridge MCP server."""
    bridge = OntosphereBridge()
    await bridge.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
