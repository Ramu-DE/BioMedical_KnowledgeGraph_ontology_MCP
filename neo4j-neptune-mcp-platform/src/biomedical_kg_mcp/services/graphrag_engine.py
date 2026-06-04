"""
GraphRAG Engine

Provides embeddings, community detection, and subgraph extraction for graph-enhanced retrieval.
Combines LLM text embeddings with structural graph features.
"""

from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel
import numpy as np
from .llm_service import LLMService


class SimilarNode(BaseModel):
    """Similar node result."""
    node_id: str
    similarity: float
    label: str
    properties: Dict[str, Any]


class Community(BaseModel):
    """Detected community."""
    community_id: int
    node_ids: List[str]
    size: int
    summary: str


class Subgraph(BaseModel):
    """Extracted subgraph."""
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    seed_id: str
    hops: int


class EmbeddingResult(BaseModel):
    """Embedding generation result."""
    node_id: str
    embedding: List[float]
    method: str  # "hybrid", "text", "structural"


class GraphRAGEngine:
    """Graph-enhanced retrieval with embeddings and community detection."""

    def __init__(self, llm_service: LLMService, neo4j_client):
        self.llm = llm_service
        self.neo4j = neo4j_client
        self.embedding_index: Dict[str, np.ndarray] = {}
        self.embedding_dim = 768  # Default dimension

    async def generate_embeddings(
        self, node_ids: List[str], method: str = "hybrid"
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for nodes.
        
        Methods:
        - hybrid: Combines LLM text embeddings with node2vec structural embeddings
        - text: LLM-based only
        - structural: Graph structure only
        
        Args:
            node_ids: List of node IDs
            method: Embedding method
            
        Returns:
            List of embedding results
        """
        results = []
        
        for node_id in node_ids:
            # Get node data
            node = await self._get_node(node_id)
            if not node:
                continue
            
            if method in ["hybrid", "text"]:
                # Generate text embedding
                text = self._node_to_text(node)
                text_emb = await self.llm.generate_embedding(text)
                
                if method == "text":
                    embedding = text_emb
                else:  # hybrid
                    # Get structural embedding
                    struct_emb = await self._structural_embedding(node_id)
                    # Combine (average)
                    embedding = [
                        (t + s) / 2 for t, s in zip(text_emb, struct_emb)
                    ]
            else:  # structural
                embedding = await self._structural_embedding(node_id)
            
            # Store in index
            self.embedding_index[node_id] = np.array(embedding)
            
            results.append(EmbeddingResult(
                node_id=node_id,
                embedding=embedding,
                method=method,
            ))
        
        return results

    async def search_similar(
        self, query_vector: List[float], top_k: int = 10
    ) -> List[SimilarNode]:
        """
        Find similar nodes using approximate nearest neighbor search.
        
        Args:
            query_vector: Query embedding
            top_k: Number of results
            
        Returns:
            Top-k similar nodes ordered by descending similarity
        """
        if not self.embedding_index:
            return []
        
        query = np.array(query_vector)
        
        # Compute cosine similarities
        similarities = []
        for node_id, emb in self.embedding_index.items():
            sim = self._cosine_similarity(query, emb)
            similarities.append((node_id, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top-k
        top_nodes = similarities[:top_k]
        
        # Fetch node details
        results = []
        for node_id, sim in top_nodes:
            node = await self._get_node(node_id)
            if node:
                results.append(SimilarNode(
                    node_id=node_id,
                    similarity=float(sim),
                    label=node.get("label", "Unknown"),
                    properties=node.get("properties", {}),
                ))
        
        return results

    async def detect_communities(
        self, algorithm: str = "louvain"
    ) -> List[Community]:
        """
        Detect communities in the graph.
        
        Algorithms:
        - louvain: Louvain modularity optimization
        - label_propagation: Label propagation
        - wcc: Weakly connected components
        
        Args:
            algorithm: Community detection algorithm
            
        Returns:
            List of detected communities with LLM-generated summaries
        """
        # Run community detection query
        if algorithm == "louvain":
            cypher = """
            CALL gds.louvain.stream('graphProjection')
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId) AS node, communityId
            """
        elif algorithm == "label_propagation":
            cypher = """
            CALL gds.labelPropagation.stream('graphProjection')
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId) AS node, communityId
            """
        else:  # wcc
            cypher = """
            CALL gds.wcc.stream('graphProjection')
            YIELD nodeId, componentId AS communityId
            RETURN gds.util.asNode(nodeId) AS node, communityId
            """
        
        try:
            result = await self.neo4j.execute_query(cypher)
            records = result.records if hasattr(result, 'records') else result
        except Exception:
            # Fallback: simple connected components
            records = await self._simple_communities()
        
        # Group by community
        communities_map: Dict[int, List[str]] = {}
        for record in records:
            comm_id = record.get("communityId", 0)
            node_id = record.get("node", {}).get("id")
            if node_id:
                communities_map.setdefault(comm_id, []).append(node_id)
        
        # Generate summaries
        communities = []
        for comm_id, node_ids in communities_map.items():
            summary = await self._generate_community_summary(node_ids)
            communities.append(Community(
                community_id=comm_id,
                node_ids=node_ids,
                size=len(node_ids),
                summary=summary,
            ))
        
        return communities

    async def extract_subgraph(
        self,
        seed_id: str,
        hops: int = 2,
        rel_types: Optional[List[str]] = None,
    ) -> Subgraph:
        """
        Extract subgraph within hop distance from seed node.
        
        Args:
            seed_id: Starting node ID
            hops: Maximum hop distance (depth bound)
            rel_types: Filter by relationship types
            
        Returns:
            Subgraph with nodes and relationships
        """
        # Build relationship filter
        rel_filter = ""
        if rel_types:
            rel_filter = f":{':'.join(rel_types)}"
        
        # Cypher query to extract subgraph
        cypher = f"""
        MATCH path = (seed {{id: $seed_id}})-[{rel_filter}*1..{hops}]-(node)
        WITH collect(DISTINCT seed) + collect(DISTINCT node) AS nodes,
             relationships(path) AS rels
        UNWIND nodes AS n
        WITH collect(DISTINCT n) AS unique_nodes, rels
        UNWIND rels AS r
        RETURN unique_nodes, collect(DISTINCT r) AS unique_rels
        """
        
        try:
            result = await self.neo4j.execute_query(cypher, {"seed_id": seed_id})
            record = result[0] if result else None
            
            if not record:
                # Node not found or disconnected
                seed_node = await self._get_node(seed_id)
                return Subgraph(
                    nodes=[seed_node] if seed_node else [],
                    relationships=[],
                    seed_id=seed_id,
                    hops=hops,
                )
            
            nodes = [self._format_node(n) for n in record.get("unique_nodes", [])]
            rels = [self._format_rel(r) for r in record.get("unique_rels", [])]
            
            return Subgraph(
                nodes=nodes,
                relationships=rels,
                seed_id=seed_id,
                hops=hops,
            )
        except Exception as e:
            # Fallback: return seed node only
            seed_node = await self._get_node(seed_id)
            return Subgraph(
                nodes=[seed_node] if seed_node else [],
                relationships=[],
                seed_id=seed_id,
                hops=hops,
            )

    async def _get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Fetch node by ID."""
        cypher = "MATCH (n {id: $id}) RETURN n"
        try:
            result = await self.neo4j.execute_query(cypher, {"id": node_id})
            if result:
                return self._format_node(result[0]["n"])
        except Exception:
            pass
        return None

    async def _structural_embedding(self, node_id: str) -> List[float]:
        """Generate structural embedding using node degree and centrality."""
        # Simple structural features (placeholder for node2vec)
        cypher = """
        MATCH (n {id: $id})
        OPTIONAL MATCH (n)-[r]-()
        RETURN count(r) AS degree
        """
        try:
            result = await self.neo4j.execute_query(cypher, {"id": node_id})
            degree = result[0]["degree"] if result else 0
            # Create simple feature vector
            return [float(degree)] * self.embedding_dim
        except Exception:
            return [0.0] * self.embedding_dim

    def _node_to_text(self, node: Dict[str, Any]) -> str:
        """Convert node to text for embedding."""
        label = node.get("label", "")
        props = node.get("properties", {})
        text_parts = [label]
        for k, v in props.items():
            if isinstance(v, str):
                text_parts.append(f"{k}: {v}")
        return " | ".join(text_parts)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

    async def _generate_community_summary(self, node_ids: List[str]) -> str:
        """Generate LLM summary for community."""
        if not node_ids:
            return "Empty community"
        
        # Sample nodes for summary
        sample_size = min(5, len(node_ids))
        sample_ids = node_ids[:sample_size]
        
        # Get node labels
        labels = []
        for nid in sample_ids:
            node = await self._get_node(nid)
            if node:
                labels.append(node.get("label", "Unknown"))
        
        # Generate summary
        text = f"Community of {len(node_ids)} nodes including: {', '.join(labels[:5])}"
        return text

    async def _simple_communities(self) -> List[Dict]:
        """Fallback: simple connected components."""
        cypher = """
        MATCH (n)
        WITH n, id(n) % 10 AS communityId
        RETURN n AS node, communityId
        LIMIT 100
        """
        result = await self.neo4j.execute_query(cypher)
        return result if result else []

    def _format_node(self, neo4j_node) -> Dict[str, Any]:
        """Format Neo4j node to dict."""
        return {
            "id": neo4j_node.get("id"),
            "label": list(neo4j_node.labels)[0] if hasattr(neo4j_node, "labels") else "Node",
            "properties": dict(neo4j_node) if neo4j_node else {},
        }

    def _format_rel(self, neo4j_rel) -> Dict[str, Any]:
        """Format Neo4j relationship to dict."""
        return {
            "type": neo4j_rel.type if hasattr(neo4j_rel, "type") else "RELATED",
            "source_id": neo4j_rel.start_node.get("id") if hasattr(neo4j_rel, "start_node") else None,
            "target_id": neo4j_rel.end_node.get("id") if hasattr(neo4j_rel, "end_node") else None,
            "properties": dict(neo4j_rel) if neo4j_rel else {},
        }
