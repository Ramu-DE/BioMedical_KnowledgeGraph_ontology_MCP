"""
Neptune Streams CDC Reader

Reads Neptune database change streams and syncs changes to Neo4j Aura.
Implements ADD → MERGE, REMOVE → DELETE sync rules.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import httpx
import asyncio
from redis.asyncio import Redis
from .sigv4_auth import SigV4Authenticator
from .rdf_lpg_converter import RDFLPGConverter


class StreamRecord(BaseModel):
    """Neptune stream record."""
    commit_num: int
    commit_timestamp: datetime
    event_id: str
    operation: str  # "ADD" or "REMOVE"
    data: Dict[str, Any]


class NeptuneStreamReader:
    """Reads Neptune Streams for CDC synchronization."""

    def __init__(
        self,
        cluster_endpoint: str,
        region: str,
        redis_client: Redis,
        converter: RDFLPGConverter,
        neo4j_client,
    ):
        self.cluster_endpoint = cluster_endpoint
        self.region = region
        self.redis = redis_client
        self.converter = converter
        self.neo4j = neo4j_client
        self.authenticator = SigV4Authenticator(region)
        self.stream_endpoint = f"https://{cluster_endpoint}:8182/gremlin/stream"
        self.checkpoint_key = "neptune_streams:checkpoint"
        self.poll_interval = 5  # seconds
        self.batch_size = 100

    async def poll(self) -> List[StreamRecord]:
        """
        Poll Neptune Streams for new records since last checkpoint.
        
        Returns:
            List of stream records
        """
        checkpoint = await self._load_checkpoint()
        
        params = {
            "commitNum": checkpoint if checkpoint else -1,
            "opNum": 0,
            "limit": self.batch_size,
        }
        
        try:
            signed_request = self.authenticator.sign_request(
                method="GET",
                url=self.stream_endpoint,
                params=params,
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.stream_endpoint,
                    params=params,
                    headers=signed_request["headers"],
                )
                response.raise_for_status()
                
            data = response.json()
            records = self._parse_records(data.get("records", []))
            return records
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 410:  # Gone - retention gap
                await self.handle_retention_gap()
            raise

    def _parse_records(self, raw_records: List[Dict]) -> List[StreamRecord]:
        """Parse raw Neptune stream records."""
        records = []
        for raw in raw_records:
            record = StreamRecord(
                commit_num=raw["commitNum"],
                commit_timestamp=datetime.fromtimestamp(raw["commitTimestamp"] / 1000),
                event_id=raw["eventId"],
                operation=raw["op"],
                data=raw["data"],
            )
            records.append(record)
        return records

    async def process_record(self, record: StreamRecord) -> None:
        """
        Process a single stream record with sync rules.
        
        Rules:
        - ADD → MERGE into Neo4j
        - REMOVE → DELETE from Neo4j
        
        Args:
            record: Stream record to process
        """
        if record.operation == "ADD":
            await self._process_add(record)
        elif record.operation == "REMOVE":
            await self._process_remove(record)

    async def _process_add(self, record: StreamRecord) -> None:
        """Handle ADD operation: MERGE into Neo4j."""
        # Convert RDF to LPG
        nodes, relationships = await self.converter.rdf_to_lpg(record.data)
        
        # MERGE nodes into Neo4j
        for node in nodes:
            cypher = f"""
            MERGE (n:{node['label']} {{id: $id}})
            SET n += $properties
            """
            await self.neo4j.execute_query(
                cypher,
                {"id": node["id"], "properties": node["properties"]},
            )
        
        # MERGE relationships
        for rel in relationships:
            cypher = f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            MERGE (a)-[r:{rel['type']}]->(b)
            SET r += $properties
            """
            await self.neo4j.execute_query(
                cypher,
                {
                    "source_id": rel["source_id"],
                    "target_id": rel["target_id"],
                    "properties": rel.get("properties", {}),
                },
            )

    async def _process_remove(self, record: StreamRecord) -> None:
        """Handle REMOVE operation: DELETE from Neo4j."""
        entity_id = record.data.get("id")
        if not entity_id:
            return
        
        # Delete node and its relationships
        cypher = """
        MATCH (n {id: $id})
        DETACH DELETE n
        """
        await self.neo4j.execute_query(cypher, {"id": entity_id})

    async def save_checkpoint(self, commit_num: int) -> None:
        """
        Save checkpoint to Redis.
        
        Args:
            commit_num: Commit number to checkpoint
        """
        await self.redis.set(self.checkpoint_key, str(commit_num))

    async def _load_checkpoint(self) -> Optional[int]:
        """Load last checkpoint from Redis."""
        checkpoint = await self.redis.get(self.checkpoint_key)
        return int(checkpoint) if checkpoint else None

    async def handle_retention_gap(self) -> None:
        """
        Handle retention gap by triggering full resync.
        
        When checkpoint is behind retention window, perform full sync
        from Neptune to Neo4j.
        """
        # Reset checkpoint
        await self.redis.delete(self.checkpoint_key)
        
        # Trigger full resync (would call sync_from_neptune tool)
        # This is a signal that full resync is needed
        await self.redis.set("neptune_streams:needs_full_resync", "1")

    async def run(self) -> None:
        """
        Run continuous stream reader loop.
        
        Polls every poll_interval seconds, processes records, and saves checkpoints.
        """
        while True:
            try:
                records = await self.poll()
                
                if records:
                    # Process records
                    for record in records:
                        await self.process_record(record)
                    
                    # Save checkpoint after successful batch
                    last_commit = max(r.commit_num for r in records)
                    await self.save_checkpoint(last_commit)
                    
                    print(f"Processed {len(records)} records, checkpoint: {last_commit}")
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                print(f"Stream reader error: {e}")
                await asyncio.sleep(self.poll_interval * 2)  # Back off on error
