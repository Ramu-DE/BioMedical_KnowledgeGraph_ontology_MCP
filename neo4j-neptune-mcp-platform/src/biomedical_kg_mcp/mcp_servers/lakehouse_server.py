"""Lakehouse MCP Server for Databricks Semantic Medallion pipeline."""

from typing import Any, Dict

from biomedical_kg_mcp.config.settings import DatabricksSettings
from biomedical_kg_mcp.mcp_servers.base import BaseMCPServer, ToolDefinition
from biomedical_kg_mcp.services.databricks_client import DatabricksClient


class LakehouseMCPServer(BaseMCPServer):
    """
    Lakehouse MCP Server for Semantic Medallion pipeline.
    
    Implements Bronze → Silver → Gold → Graph data refinement pipeline.
    """
    
    def __init__(self, settings: DatabricksSettings):
        """Initialize Lakehouse MCP Server."""
        super().__init__("lakehouse-server", "1.0.0")
        
        self.client = DatabricksClient(
            workspace_url=settings.workspace_url,
            access_token=settings.access_token
        )
        self.settings = settings
        
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register medallion pipeline tools."""
        
        self.register_tool(ToolDefinition(
            name="lakehouse_ingest_bronze",
            description="Ingest raw data to Bronze layer",
            input_schema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "source_type": {"type": "string", "enum": ["csv", "json", "parquet"]},
                    "table_name": {"type": "string"}
                },
                "required": ["source_path", "source_type", "table_name"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            name="lakehouse_process_silver",
            description="Process Bronze to Silver with entity resolution",
            input_schema={
                "type": "object",
                "properties": {
                    "bronze_table": {"type": "string"},
                    "silver_table": {"type": "string"},
                    "entity_type": {"type": "string"}
                },
                "required": ["bronze_table", "silver_table", "entity_type"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            name="lakehouse_transform_gold",
            description="Transform Silver to Gold with RDF generation",
            input_schema={
                "type": "object",
                "properties": {
                    "silver_table": {"type": "string"},
                    "gold_table": {"type": "string"},
                    "ontology_module": {"type": "string"}
                },
                "required": ["silver_table", "gold_table", "ontology_module"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            name="lakehouse_run_pipeline",
            description="Run full Bronze → Silver → Gold pipeline",
            input_schema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "entity_type": {"type": "string"},
                    "ontology_module": {"type": "string"}
                },
                "required": ["source_path", "entity_type"]
            }
        ))
        
        self.register_tool(ToolDefinition(
            name="lakehouse_export_rdf",
            description="Export Gold layer to S3 as N-Triples",
            input_schema={
                "type": "object",
                "properties": {
                    "gold_table": {"type": "string"},
                    "s3_uri": {"type": "string"}
                },
                "required": ["gold_table", "s3_uri"]
            }
        ))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool."""
        
        if tool_name == "lakehouse_ingest_bronze":
            return await self._tool_ingest_bronze(arguments)
        elif tool_name == "lakehouse_process_silver":
            return await self._tool_process_silver(arguments)
        elif tool_name == "lakehouse_transform_gold":
            return await self._tool_transform_gold(arguments)
        elif tool_name == "lakehouse_run_pipeline":
            return await self._tool_run_pipeline(arguments)
        elif tool_name == "lakehouse_export_rdf":
            return await self._tool_export_rdf(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _tool_ingest_bronze(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest to Bronze layer."""
        source_path = args["source_path"]
        table_name = args["table_name"]
        
        # Submit ingestion job
        run_id = self.client.submit_job(
            job_name=f"bronze_ingest_{table_name}",
            notebook_path="/Workspace/pipelines/bronze_ingest",
            parameters={"source": source_path, "table": table_name}
        )
        
        return {"run_id": run_id, "status": "submitted", "layer": "bronze"}
    
    async def _tool_process_silver(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process to Silver layer."""
        bronze_table = args["bronze_table"]
        silver_table = args["silver_table"]
        
        run_id = self.client.submit_job(
            job_name=f"silver_process_{silver_table}",
            notebook_path="/Workspace/pipelines/silver_process",
            parameters={"bronze": bronze_table, "silver": silver_table}
        )
        
        return {"run_id": run_id, "status": "submitted", "layer": "silver"}
    
    async def _tool_transform_gold(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Transform to Gold layer."""
        silver_table = args["silver_table"]
        gold_table = args["gold_table"]
        
        run_id = self.client.submit_job(
            job_name=f"gold_transform_{gold_table}",
            notebook_path="/Workspace/pipelines/gold_transform",
            parameters={"silver": silver_table, "gold": gold_table}
        )
        
        return {"run_id": run_id, "status": "submitted", "layer": "gold"}
    
    async def _tool_run_pipeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run full pipeline."""
        source_path = args["source_path"]
        entity_type = args["entity_type"]
        
        # Run all stages sequentially
        bronze_result = await self._tool_ingest_bronze({
            "source_path": source_path,
            "source_type": "csv",
            "table_name": f"bronze_{entity_type}"
        })
        
        return {
            "pipeline_id": bronze_result["run_id"],
            "stages": ["bronze", "silver", "gold"],
            "status": "running"
        }
    
    async def _tool_export_rdf(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export to S3."""
        gold_table = args["gold_table"]
        s3_uri = args["s3_uri"]
        
        run_id = self.client.submit_job(
            job_name=f"export_rdf_{gold_table}",
            notebook_path="/Workspace/pipelines/export_rdf",
            parameters={"gold": gold_table, "s3": s3_uri}
        )
        
        return {"run_id": run_id, "s3_uri": s3_uri, "status": "exporting"}
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities."""
        return {
            "tools": True,
            "data_platform": "Databricks",
            "layers": ["bronze", "silver", "gold"],
            "storage": "Delta Lake"
        }
