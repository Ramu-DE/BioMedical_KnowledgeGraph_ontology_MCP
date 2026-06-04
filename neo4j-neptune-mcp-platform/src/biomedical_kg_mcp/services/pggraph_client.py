"""
pgGraph Client for Supply/Quality Module

PostgreSQL with pgGraph extension for supply chain graph queries.
FK relationships automatically become graph edges.
"""

from typing import List, Dict, Any, Optional
import asyncpg


class PgGraphClient:
    """PostgreSQL + pgGraph client for Supply/Quality data."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=2,
            max_size=10,
        )

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def traverse(
        self, start_id: str, table: str, direction: str = "outgoing", max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Traverse graph from starting node.
        
        Args:
            start_id: Starting entity ID
            table: Starting table (manufacturing_sites, drug_batches, quality_events)
            direction: outgoing, incoming, both
            max_depth: Maximum traversal depth
            
        Returns:
            List of connected entities
        """
        query = f"""
        SELECT * FROM graph.traverse(
            start_table := '{table}',
            start_id := $1,
            direction := '{direction}',
            max_depth := {max_depth}
        )
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, start_id)
            return [dict(row) for row in rows]

    async def shortest_path(
        self, source_table: str, source_id: str, target_table: str, target_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find shortest path between two entities.
        
        Args:
            source_table: Source table name
            source_id: Source entity ID
            target_table: Target table name
            target_id: Target entity ID
            
        Returns:
            Path as list of entities, or None if no path
        """
        query = """
        SELECT * FROM graph.shortest_path(
            source_table := $1,
            source_id := $2,
            target_table := $3,
            target_id := $4
        )
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, source_table, source_id, target_table, target_id)
            return [dict(row) for row in rows] if rows else None

    async def neighbors(
        self, table: str, entity_id: str, edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get immediate neighbors of entity.
        
        Args:
            table: Entity table
            entity_id: Entity ID
            edge_type: Filter by edge type (FK name)
            
        Returns:
            List of neighbor entities
        """
        if edge_type:
            query = f"""
            SELECT * FROM graph.neighbors(
                table_name := '{table}',
                entity_id := $1,
                edge_type := '{edge_type}'
            )
            """
        else:
            query = f"""
            SELECT * FROM graph.neighbors(
                table_name := '{table}',
                entity_id := $1
            )
            """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, entity_id)
            return [dict(row) for row in rows]

    async def subgraph(
        self, table: str, entity_id: str, depth: int = 2
    ) -> Dict[str, Any]:
        """
        Extract connected subgraph around entity.
        
        Args:
            table: Starting table
            entity_id: Starting entity ID
            depth: BFS depth
            
        Returns:
            Subgraph with nodes and edges
        """
        query = f"""
        SELECT * FROM graph.bfs(
            start_table := '{table}',
            start_id := $1,
            depth := {depth}
        )
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, entity_id)
            
            nodes = []
            edges = []
            for row in rows:
                if row.get("node_type"):
                    nodes.append(dict(row))
                elif row.get("edge_type"):
                    edges.append(dict(row))
            
            return {"nodes": nodes, "edges": edges}

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or []))
            return [dict(row) for row in rows]
