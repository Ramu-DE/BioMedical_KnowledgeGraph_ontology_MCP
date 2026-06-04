"""Unit tests for Neptune MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from biomedical_kg_mcp.config.settings import NeptuneSettings
from biomedical_kg_mcp.mcp_servers.neptune_server import NeptuneMCPServer


@pytest.fixture
def neptune_settings():
    """Create test Neptune settings."""
    return NeptuneSettings(
        cluster_endpoint="test-cluster.us-east-1.neptune.amazonaws.com",
        port=8182,
        region="us-east-1",
        iam_role_arn="arn:aws:iam::123456789012:role/NeptuneLoadRole",
        use_iam_auth=True
    )


@pytest.fixture
def mock_authenticator():
    """Create mock SigV4 authenticator."""
    auth = MagicMock()
    auth.sign_request = MagicMock(return_value={
        "Authorization": "AWS4-HMAC-SHA256 Credential=...",
        "X-Amz-Date": "20240101T000000Z"
    })
    return auth


@pytest.mark.asyncio
class TestNeptuneMCPServer:
    """Test suite for Neptune MCP Server."""
    
    async def test_server_initialization(self, neptune_settings):
        """Test server initializes with correct name and tools."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator'):
            server = NeptuneMCPServer(neptune_settings)
            
            assert server.server_name == "neptune-server"
            assert len(server.list_tools()) == 5
            
            tool_names = [tool.name for tool in server.list_tools()]
            assert "neptune_sparql" in tool_names
            assert "neptune_cypher" in tool_names
            assert "neptune_bulk_load" in tool_names
            assert "neptune_load_status" in tool_names
            assert "neptune_status" in tool_names
    
    async def test_neptune_sparql_tool(self, neptune_settings, mock_authenticator):
        """Test neptune_sparql executes SPARQL query."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": {
                    "bindings": [
                        {"drug": {"value": "http://example.org/Drug1"}},
                        {"drug": {"value": "http://example.org/Drug2"}}
                    ]
                }
            }
            mock_response.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(return_value=mock_response)
            
            result = await server.call_tool("neptune_sparql", {
                "query": "SELECT ?drug WHERE { ?drug a :Drug }"
            })
            
            assert result["count"] == 2
            assert len(result["results"]) == 2
    
    async def test_neptune_cypher_tool(self, neptune_settings, mock_authenticator):
        """Test neptune_cypher executes openCypher query."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"n": {"id": "D001", "name": "Drug1"}},
                    {"n": {"id": "D002", "name": "Drug2"}}
                ]
            }
            mock_response.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(return_value=mock_response)
            
            result = await server.call_tool("neptune_cypher", {
                "query": "MATCH (n:Drug) RETURN n",
                "parameters": {}
            })
            
            assert result["count"] == 2
    
    async def test_neptune_bulk_load_tool(self, neptune_settings, mock_authenticator):
        """Test neptune_bulk_load initiates load job."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "200 OK",
                "payload": {"loadId": "load-12345"}
            }
            mock_response.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(return_value=mock_response)
            
            result = await server.call_tool("neptune_bulk_load", {
                "s3_uri": "s3://my-bucket/data.nt",
                "format": "ntriples",
                "named_graph": "https://biomedkg.org/graph/drugs"
            })
            
            assert result["job_id"] == "load-12345"
            assert result["status"] == "200 OK"
    
    async def test_neptune_load_status_tool(self, neptune_settings, mock_authenticator):
        """Test neptune_load_status checks job status."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "payload": {
                    "overallStatus": {
                        "status": "LOAD_COMPLETED",
                        "totalRecords": 1000,
                        "errors": []
                    }
                }
            }
            mock_response.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(return_value=mock_response)
            
            result = await server.call_tool("neptune_load_status", {
                "job_id": "load-12345"
            })
            
            assert result["status"] == "LOAD_COMPLETED"
            assert result["records_loaded"] == 1000
            assert len(result["errors"]) == 0
    
    async def test_neptune_status_tool(self, neptune_settings, mock_authenticator):
        """Test neptune_status returns cluster status."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "version": "1.2.0.0",
                "dbEngineVersion": "1.2.0.0.R5"
            }
            mock_response.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(return_value=mock_response)
            
            result = await server.call_tool("neptune_status", {})
            
            assert result["status"] == "healthy"
            assert "version" in result
    
    async def test_sigv4_signing_called(self, neptune_settings, mock_authenticator):
        """Test that SigV4 signing is applied to requests."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_response.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(return_value=mock_response)
            
            await server.call_tool("neptune_status", {})
            
            # Verify sign_request was called
            mock_authenticator.sign_request.assert_called()
    
    async def test_http_429_retry_with_backoff(self, neptune_settings, mock_authenticator):
        """Test retry logic for HTTP 429 throttling."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            
            # First two calls return 429, third succeeds
            mock_response_429 = AsyncMock()
            mock_response_429.status_code = 429
            
            mock_response_200 = AsyncMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {"status": "healthy"}
            mock_response_200.raise_for_status = MagicMock()
            
            server.client.request = AsyncMock(
                side_effect=[mock_response_429, mock_response_429, mock_response_200]
            )
            
            result = await server.call_tool("neptune_status", {})
            
            # Should have retried and eventually succeeded
            assert server.client.request.call_count == 3
            assert result["status"] == "healthy"
    
    async def test_get_capabilities(self, neptune_settings):
        """Test server returns correct capabilities."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator'):
            server = NeptuneMCPServer(neptune_settings)
            
            capabilities = server.get_capabilities()
            
            assert capabilities["tools"] is True
            assert capabilities["graph_database"] == "AWS Neptune"
            assert "SPARQL" in capabilities["query_languages"]
            assert "openCypher" in capabilities["query_languages"]
            assert capabilities["authentication"] == "AWS IAM SigV4"
    
    async def test_server_stop_closes_client(self, neptune_settings, mock_authenticator):
        """Test server.stop() closes HTTP client."""
        with patch('biomedical_kg_mcp.mcp_servers.neptune_server.SigV4Authenticator', return_value=mock_authenticator):
            server = NeptuneMCPServer(neptune_settings)
            server.client.aclose = AsyncMock()
            
            await server.stop()
            
            server.client.aclose.assert_called_once()
