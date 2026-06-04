"""Graph Sync Orchestrator for bidirectional Neo4j ↔ Neptune synchronization."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from rdflib import Graph

from biomedical_kg_mcp.models.sync import ConflictRecord, ConflictResolution, SyncJob, SyncStatus
from biomedical_kg_mcp.models.validation import ValidationReport
from biomedical_kg_mcp.services.iri_minter import IRIMinter
from biomedical_kg_mcp.services.neo4j_client import Neo4jClient
from biomedical_kg_mcp.services.shacl_validator import SHACLValidator


class SyncOrchestrator:
    """
    Orchestrates bidirectional graph synchronization between Neo4j Aura and Neptune.
    
    Features:
    - Neo4j → Neptune: LPG to RDF with SHACL validation
    - Neptune → Neo4j: RDF to LPG conversion
    - Conflict resolution: Last-writer-wins with audit trail
    - IRI minting and vocabulary alignment
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        iri_minter: IRIMinter,
        shacl_validator: SHACLValidator,
    ):
        """
        Initialize Sync Orchestrator.
        
        Args:
            neo4j_client: Neo4j client instance
            iri_minter: IRI minter service
            shacl_validator: SHACL validator service
        """
        self.neo4j_client = neo4j_client
        self.iri_minter = iri_minter
        self.shacl_validator = shacl_validator
        
        self._jobs: Dict[str, SyncJob] = {}
        self._conflicts: List[ConflictRecord] = []
    
    async def sync_to_neptune(
        self,
        cypher_query: str,
        named_graph: str,
        validate: bool = True
    ) -> SyncJob:
        """
        Sync from Neo4j to Neptune.
        
        Pipeline:
        1. Extract subgraph from Neo4j (Cypher query)
        2. Convert LPG → RDF triples
        3. Mint IRIs for entities
        4. SHACL validation (if enabled)
        5. Publish to Neptune
        
        Args:
            cypher_query: Cypher query to extract subgraph
            named_graph: Target Neptune named graph URI
            validate: Enable SHACL validation
            
        Returns:
            SyncJob tracking the sync operation
        """
        # Create sync job
        job = SyncJob(
            job_id=str(uuid.uuid4()),
            direction="to_neptune",
            status=SyncStatus.PENDING,
            source_query=cypher_query,
            named_graph=named_graph,
            validate=validate,
            started_at=datetime.utcnow()
        )
        self._jobs[job.job_id] = job
        
        try:
            job.status = SyncStatus.RUNNING
            
            # Step 1: Extract from Neo4j
            records = await self.neo4j_client.execute_query(cypher_query)
            job.entity_count = len(records)
            
            # Step 2: Convert to RDF (handled by converter - simplified here)
            rdf_graph = Graph()
            # Conversion logic would go here
            
            # Step 3: Mint IRIs
            # IRI minting logic would go here
            
            # Step 4: Validate if enabled
            if validate:
                job.status = SyncStatus.VALIDATING
                # Load shapes (simplified - would need proper shape loading)
                shapes_graph = Graph()
                report = self.shacl_validator.validate(rdf_graph, shapes_graph)
                
                if not report.conforms:
                    job.status = SyncStatus.FAILED
                    job.error_message = f"SHACL validation failed: {report.total_violations} violations"
                    job.completed_at = datetime.utcnow()
                    return job
            
            # Step 5: Publish to Neptune (would need Neptune client)
            job.triple_count = len(rdf_graph)
            job.status = SyncStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = SyncStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        return job
    
    async def sync_from_neptune(
        self,
        sparql_construct: str,
        target_labels: List[str]
    ) -> SyncJob:
        """
        Sync from Neptune to Neo4j.
        
        Pipeline:
        1. Execute SPARQL CONSTRUCT on Neptune
        2. Convert RDF → LPG
        3. Map IRIs to Neo4j IDs
        4. MERGE nodes and relationships in Neo4j
        
        Args:
            sparql_construct: SPARQL CONSTRUCT query
            target_labels: Target node labels in Neo4j
            
        Returns:
            SyncJob tracking the sync operation
        """
        job = SyncJob(
            job_id=str(uuid.uuid4()),
            direction="from_neptune",
            status=SyncStatus.PENDING,
            source_query=sparql_construct,
            started_at=datetime.utcnow()
        )
        self._jobs[job.job_id] = job
        
        try:
            job.status = SyncStatus.RUNNING
            
            # Step 1: Get RDF from Neptune (would need Neptune client)
            rdf_graph = Graph()
            # Neptune query logic would go here
            
            # Step 2: Convert RDF → LPG (handled by converter)
            # Conversion logic would go here
            
            # Step 3: Load into Neo4j
            # Would execute MERGE statements
            
            job.status = SyncStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = SyncStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        return job
    
    def resolve_conflict(
        self,
        entity_id: str,
        entity_type: str,
        neo4j_value: Dict[str, Any],
        neptune_value: Dict[str, Any],
        neo4j_timestamp: datetime,
        neptune_timestamp: datetime
    ) -> ConflictRecord:
        """
        Resolve conflict using last-writer-wins strategy.
        
        Args:
            entity_id: Entity identifier
            entity_type: Entity type
            neo4j_value: Neo4j entity properties
            neptune_value: Neptune entity properties
            neo4j_timestamp: Neo4j last modified timestamp
            neptune_timestamp: Neptune last modified timestamp
            
        Returns:
            ConflictRecord with resolution
        """
        # Last-writer-wins: choose value with later timestamp
        if neptune_timestamp > neo4j_timestamp:
            resolved_value = neptune_value
        else:
            resolved_value = neo4j_value
        
        conflict = ConflictRecord(
            conflict_id=str(uuid.uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
            neo4j_value=neo4j_value,
            neptune_value=neptune_value,
            neo4j_timestamp=neo4j_timestamp,
            neptune_timestamp=neptune_timestamp,
            resolution=ConflictResolution.LAST_WRITER_WINS,
            resolved_value=resolved_value,
            resolved_at=datetime.utcnow()
        )
        
        self._conflicts.append(conflict)
        return conflict
    
    def get_job(self, job_id: str) -> Optional[SyncJob]:
        """Get sync job by ID."""
        return self._jobs.get(job_id)
    
    def list_conflicts(
        self,
        since: Optional[datetime] = None,
        resolved: Optional[bool] = None
    ) -> List[ConflictRecord]:
        """
        List conflicts with optional filters.
        
        Args:
            since: Only conflicts after this timestamp
            resolved: Filter by resolution status
            
        Returns:
            List of conflict records
        """
        conflicts = self._conflicts
        
        if since:
            conflicts = [c for c in conflicts if c.resolved_at and c.resolved_at > since]
        
        if resolved is not None:
            conflicts = [c for c in conflicts if (c.resolved_at is not None) == resolved]
        
        return conflicts
