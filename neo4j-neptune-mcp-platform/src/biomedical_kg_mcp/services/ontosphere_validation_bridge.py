"""Ontosphere SHACL Validation Bridge.

Coordinates validation between Ontosphere's OWL reasoning and 
the platform's SHACL validator, then syncs to Neptune via Graph Sync Server.
"""

from typing import Dict, Any, Optional
import logging
from rdflib import Graph

from .ontosphere_client import OntosphereClient
from .shacl_validator import SHACLValidator
from ..mcp_servers.graph_sync_server import GraphSyncOrchestrator

logger = logging.getLogger(__name__)


class OntosphereValidationBridge:
    """Bridge OWL reasoning in Ontosphere with SHACL validation and Neptune sync."""
    
    def __init__(
        self,
        ontosphere_client: OntosphereClient,
        shacl_validator: SHACLValidator,
        sync_orchestrator: GraphSyncOrchestrator
    ):
        self.ontosphere = ontosphere_client
        self.shacl = shacl_validator
        self.sync = sync_orchestrator
    
    async def validate_and_sync(
        self,
        run_owl_reasoning: bool = True,
        shacl_shapes_graph: Optional[Graph] = None
    ) -> Dict[str, Any]:
        """Full validation pipeline: OWL → SHACL → Neptune sync."""
        
        results = {
            "owl_reasoning": None,
            "shacl_validation": None,
            "neptune_sync": None,
            "status": "pending"
        }
        
        # Step 1: Run OWL reasoning in Ontosphere
        if run_owl_reasoning:
            logger.info("Running OWL 2 DL reasoning in Ontosphere")
            owl_result = await self.ontosphere.run_reasoning()
            results["owl_reasoning"] = {
                "inferred_triples": owl_result.get("inferred_triples", 0),
                "status": owl_result.get("status")
            }
            
            if owl_result.get("status") == "error":
                results["status"] = "owl_reasoning_failed"
                return results
        
        # Step 2: Export RDF from Ontosphere
        logger.info("Exporting RDF from Ontosphere")
        export_result = await self.ontosphere.export_graph("turtle")
        rdf_data = export_result.get("data", "")
        
        if not rdf_data:
            results["status"] = "export_failed"
            return results
        
        # Parse into rdflib Graph
        data_graph = Graph()
        data_graph.parse(data=rdf_data, format="turtle")
        
        # Step 3: SHACL validation
        logger.info("Running SHACL validation")
        validation_result = self.shacl.validate(data_graph, shacl_shapes_graph)
        results["shacl_validation"] = {
            "conforms": validation_result.conforms,
            "violations": len(validation_result.violations),
            "warnings": len(validation_result.warnings)
        }
        
        if not validation_result.conforms:
            results["status"] = "shacl_validation_failed"
            results["shacl_validation"]["violation_details"] = [
                {
                    "severity": v.severity,
                    "message": v.message,
                    "focus_node": str(v.focus_node)
                }
                for v in validation_result.violations
            ]
            return results
        
        # Step 4: Sync to Neptune
        logger.info("Syncing validated RDF to Neptune")
        try:
            sync_result = await self.sync.sync_to_neptune(
                data_graph,
                validation_report=validation_result
            )
            
            results["neptune_sync"] = {
                "triples_synced": sync_result.get("triples_synced", 0),
                "sync_id": sync_result.get("sync_id")
            }
            results["status"] = "success"
            
        except Exception as e:
            logger.error(f"Neptune sync failed: {e}")
            results["neptune_sync"] = {"error": str(e)}
            results["status"] = "neptune_sync_failed"
        
        return results
    
    async def preview_validation(
        self,
        shacl_shapes_graph: Optional[Graph] = None
    ) -> Dict[str, Any]:
        """Preview validation without syncing to Neptune."""
        
        # Export from Ontosphere
        export_result = await self.ontosphere.export_graph("turtle")
        rdf_data = export_result.get("data", "")
        
        data_graph = Graph()
        data_graph.parse(data=rdf_data, format="turtle")
        
        # SHACL validation
        validation_result = self.shacl.validate(data_graph, shacl_shapes_graph)
        
        return {
            "conforms": validation_result.conforms,
            "triple_count": len(data_graph),
            "violations": [
                {
                    "severity": v.severity,
                    "message": v.message,
                    "focus_node": str(v.focus_node),
                    "source_shape": str(v.source_shape)
                }
                for v in validation_result.violations
            ],
            "warnings": [
                {
                    "message": w.message,
                    "focus_node": str(w.focus_node)
                }
                for w in validation_result.warnings
            ]
        }
    
    async def load_and_validate_module(
        self,
        module_url: str,
        shacl_shapes_graph: Optional[Graph] = None
    ) -> Dict[str, Any]:
        """Load ontology module into Ontosphere and validate."""
        
        # Load into Ontosphere
        load_result = await self.ontosphere.load_ontology(module_url)
        
        if not load_result.get("success"):
            return {
                "status": "load_failed",
                "error": load_result.get("error")
            }
        
        # Validate
        return await self.preview_validation(shacl_shapes_graph)
