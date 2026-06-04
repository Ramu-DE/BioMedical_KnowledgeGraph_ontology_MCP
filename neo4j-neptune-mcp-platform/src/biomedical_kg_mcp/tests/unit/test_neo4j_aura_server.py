"""Unit tests for Neo4j Aura MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from biomedical_kg_mcp.config.settings import Neo4jAuraSettings
from biomedical_kg_mcp.mcp_servers.neo4j_aura_server import Neo4jAuraMCPServer


@pytest.fixture
def neo4j_settings():
    """Create test Neo4j settings."""
    return Neo4jAuraSettings(
        uri="bolt+s://test.databases.neo4j.io",
        user="neo4j",
        password="test_password",
        database="neo4j"
    )


@pytest.fixture
def mock_client():
    """Create mock Neo4j client."""
    client = AsyncMock()
    client.execute_query = AsyncMock()
    client.get_schema = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
class TestNeo4jAuraMCPServer:
    """Test suite for Neo4j Aura MCP Server."""
    
    async def test_server_initialization(self, neo4j_settings):
        """Test server initializes with correct name and tools."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient'):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            assert server.server_name == "neo4j-aura-server"
            assert server.server_version == "1.0.0"
            assert len(server.list_tools()) == 5
            
            tool_names = [tool.name for tool in server.list_tools()]
            assert "neo4j_query" in tool_names
            assert "neo4j_pathfind" in tool_names
            assert "neo4j_community" in tool_names
            assert "neo4j_expand" in tool_names
            assert "neo4j_schema" in tool_names
    
    async def test_neo4j_query_tool(self, neo4j_settings, mock_client):
        """Test neo4j_query tool executes Cypher."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            # Mock query results
            mock_client.execute_query.return_value = [
                {"name": "Drug1", "type": "Small Molecule"},
                {"name": "Drug2", "type": "Biologic"}
            ]
            
            result = await server.call_tool("neo4j_query", {
                "query": "MATCH (d:Drug) RETURN d.name as name, d.type as type",
                "parameters": {}
            })
            
            assert result["count"] == 2
            assert len(result["results"]) == 2
            mock_client.execute_query.assert_called_once()
    
    async def test_neo4j_query_with_timeout(self, neo4j_settings, mock_client):
        """Test neo4j_query respects timeout parameter."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            mock_client.execute_query.return_value = []
            
            await server.call_tool("neo4j_query", {
                "query": "MATCH (n) RETURN n",
                "timeout": 5
            })
            
            call_args = mock_client.execute_query.call_args
            assert call_args[1]["timeout"] == 5
    
    async def test_neo4j_pathfind_bfs(self, neo4j_settings, mock_client):
        """Test neo4j_pathfind with BFS algorithm."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            mock_client.execute_query.return_value = [
                {"path": ["D001", "TREATS", "DIS001"], "pathLength": 1}
            ]
            
            result = await server.call_tool("neo4j_pathfind", {
                "source_id": "D001",
                "target_id": "DIS001",
                "algorithm": "bfs"
            })
            
            assert result["count"] == 1
            assert len(result["paths"]) == 1
    
    async def test_neo4j_community_louvain(self, neo4j_settings, mock_client):
        """Test neo4j_community with Louvain algorithm."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            mock_client.execute_query.return_value = [
                {"nodeId": "D001", "communityId": 1},
                {"nodeId": "D002", "communityId": 1},
                {"nodeId": "G001", "communityId": 2}
            ]
            
            result = await server.call_tool("neo4j_community", {
                "algorithm": "louvain"
            })
            
            assert result["count"] == 3
            assert len(result["communities"]) == 3
    
    async def test_neo4j_expand_with_depth(self, neo4j_settings, mock_client):
        """Test neo4j_expand with depth parameter."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            mock_client.execute_query.return_value = [
                {"start": {"id": "D001"}, "neighbor": {"id": "DIS001"}},
                {"start": {"id": "D001"}, "neighbor": {"id": "P001"}}
            ]
            
            result = await server.call_tool("neo4j_expand", {
                "node_id": "D001",
                "depth": 2
            })
            
            assert result["count"] == 2
            assert len(result["nodes"]) == 2
    
    async def test_neo4j_expand_with_rel_types_filter(self, neo4j_settings, mock_client):
        """Test neo4j_expand with relationship type filter."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            mock_client.execute_query.return_value = []
            
            await server.call_tool("neo4j_expand", {
                "node_id": "D001",
                "depth": 1,
                "rel_types": ["TREATS", "TARGETS"]
            })
            
            # Verify query includes relationship filter
            call_args = mock_client.execute_query.call_args
            query = call_args[0][0]
            assert ":TREATS:TARGETS" in query or "rel_types" in str(call_args)
    
    async def test_neo4j_schema_tool(self, neo4j_settings, mock_client):
        """Test neo4j_schema returns graph schema."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            mock_client.get_schema.return_value = {
                "node_labels": ["Drug", "Disease", "Gene"],
                "relationship_types": ["TREATS", "TARGETS"],
                "property_keys": ["id", "name", "type"]
            }
            
            result = await server.call_tool("neo4j_schema", {})
            
            assert "node_labels" in result
            assert len(result["node_labels"]) == 3
            assert "Drug" in result["node_labels"]
            mock_client.get_schema.assert_called_once()
    
    async def test_get_capabilities(self, neo4j_settings):
        """Test server returns correct capabilities."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient'):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            capabilities = server.get_capabilities()
            
            assert capabilities["tools"] is True
            assert capabilities["graph_database"] == "Neo4j Aura"
            assert capabilities["query_language"] == "Cypher"
    
    async def test_server_stop_closes_client(self, neo4j_settings, mock_client):
        """Test server.stop() closes client connection."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient', return_value=mock_client):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            await server.stop()
            
            mock_client.close.assert_called_once()
    
    async def test_unknown_tool_raises_error(self, neo4j_settings):
        """Test calling unknown tool raises ValueError."""
        with patch('biomedical_kg_mcp.mcp_servers.neo4j_aura_server.Neo4jClient'):
            server = Neo4jAuraMCPServer(neo4j_settings)
            
            with pytest.raises(ValueError, match="Unknown tool"):
                await server.call_tool("unknown_tool", {})
