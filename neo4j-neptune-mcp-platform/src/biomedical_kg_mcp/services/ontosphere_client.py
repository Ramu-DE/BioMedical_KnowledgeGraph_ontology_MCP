"""Ontosphere Client Service.

Communicates with Ontosphere browser instance via its MCP tools.
Supports both headless (Playwright) and browser-based interaction.
"""

from typing import Any, Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)


class OntosphereClient:
    """Client for interacting with Ontosphere's MCP tool surface."""
    
    def __init__(self, ontosphere_url: str = "https://thhanke.github.io/ontosphere/"):
        self.ontosphere_url = ontosphere_url
        self._playwright_page = None
    
    async def _ensure_browser(self):
        """Initialize headless browser if needed."""
        if self._playwright_page:
            return
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("playwright required for headless Ontosphere: pip install playwright")
        
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Inject MCP polyfill
        await page.add_init_script("""
            const tools = {};
            Object.defineProperty(navigator, 'modelContext', {
                value: { registerTool: async (n, _d, _s, h) => { tools[n] = h; } },
                configurable: true,
            });
            window.__mcpTools = tools;
        """)
        
        await page.goto(self.ontosphere_url)
        
        # Register MCP tools
        await page.evaluate("""
            async () => {
                const mod = await import('/src/mcp/ontosphereMcpServer.ts');
                await mod.registerMcpTools();
            }
        """)
        
        self._playwright_page = page
    
    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an Ontosphere MCP tool."""
        await self._ensure_browser()
        
        result = await self._playwright_page.evaluate(
            """
            async ([name, params]) => {
                const tool = window.__mcpTools[name];
                if (!tool) throw new Error(`Tool ${name} not found`);
                return await tool(params);
            }
            """,
            [tool_name, params]
        )
        
        return result
    
    async def load_ontology(self, url: str) -> Dict[str, Any]:
        """Load an ontology from URL into Ontosphere."""
        logger.info(f"Loading ontology from {url}")
        return await self._call_tool("loadOntology", {"url": url})
    
    async def run_reasoning(self) -> Dict[str, Any]:
        """Run OWL 2 DL reasoning via Konclude."""
        logger.info("Running OWL reasoning")
        return await self._call_tool("runReasoning", {})
    
    async def validate_graph(self, shacl_url: Optional[str] = None) -> Dict[str, Any]:
        """Validate graph against SHACL shapes."""
        params = {}
        if shacl_url:
            params["shaclUrl"] = shacl_url
        
        logger.info("Validating graph")
        return await self._call_tool("validateGraph", params)
    
    async def export_graph(self, format: str = "turtle") -> Dict[str, Any]:
        """Export RDF graph in specified format."""
        logger.info(f"Exporting graph as {format}")
        return await self._call_tool("exportGraph", {"format": format})
    
    async def query_graph(self, sparql: str) -> Dict[str, Any]:
        """Execute SPARQL query against loaded graph."""
        logger.info(f"Querying graph: {sparql[:100]}")
        return await self._call_tool("queryGraph", {"query": sparql})
    
    async def add_node(
        self, 
        iri: str, 
        type_iri: str, 
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a node to the canvas."""
        params = {"iri": iri, "typeIri": type_iri}
        if label:
            params["label"] = label
        
        logger.info(f"Adding node {iri}")
        return await self._call_tool("addNode", params)
    
    async def add_link(
        self, 
        source_iri: str, 
        target_iri: str, 
        predicate_iri: str
    ) -> Dict[str, Any]:
        """Add a link between two nodes."""
        params = {
            "sourceIri": source_iri,
            "targetIri": target_iri,
            "predicateIri": predicate_iri
        }
        
        logger.info(f"Adding link {source_iri} -> {target_iri}")
        return await self._call_tool("addLink", params)
    
    async def run_layout(self, algorithm: str = "dagre-lr") -> Dict[str, Any]:
        """Run graph layout algorithm."""
        logger.info(f"Running layout: {algorithm}")
        return await self._call_tool("runLayout", {"algorithm": algorithm})
    
    async def expand_node(self, iri: Optional[str] = None) -> Dict[str, Any]:
        """Expand node to show annotation properties."""
        params = {}
        if iri:
            params["iri"] = iri
        
        logger.info(f"Expanding node: {iri or 'all'}")
        return await self._call_tool("expandNode", params)
    
    async def fit_canvas(self) -> Dict[str, Any]:
        """Fit canvas to viewport."""
        return await self._call_tool("fitCanvas", {})
    
    async def export_image(self, format: str = "svg") -> Dict[str, Any]:
        """Export canvas as image."""
        logger.info(f"Exporting image as {format}")
        return await self._call_tool("exportImage", {"format": format})
    
    async def close(self):
        """Close browser connection."""
        if self._playwright_page:
            await self._playwright_page.close()
            await self._playwright.stop()
            self._playwright_page = None
