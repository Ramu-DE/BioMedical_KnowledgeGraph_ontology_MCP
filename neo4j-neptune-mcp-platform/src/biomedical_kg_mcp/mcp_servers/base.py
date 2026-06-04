"""Base MCP server with JSON-RPC 2.0 protocol handling."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Tool parameter definition with JSON Schema."""
    
    type: str = Field(..., description="Parameter type (string, integer, object, array, boolean)")
    description: Optional[str] = None
    required: bool = False
    enum: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    items: Optional[Dict[str, Any]] = None
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """MCP tool definition with JSON Schema input specification."""
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for tool input")


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error."""
    
    code: int
    message: str
    data: Optional[Any] = None


class BaseMCPServer(ABC):
    """
    Abstract base class for MCP servers.
    
    Implements JSON-RPC 2.0 protocol handling, tool registration,
    and stdio/SSE transport support.
    """
    
    def __init__(self, server_name: str, server_version: str = "1.0.0"):
        self.server_name = server_name
        self.server_version = server_version
        self._tools: Dict[str, ToolDefinition] = {}
    
    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool with the MCP server."""
        self._tools[tool.name] = tool
    
    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())
    
    async def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """
        Handle incoming JSON-RPC request.
        
        Args:
            request: JSON-RPC 2.0 request
            
        Returns:
            JSON-RPC 2.0 response
        """
        try:
            if request.method == "tools/list":
                result = {"tools": [tool.model_dump() for tool in self.list_tools()]}
                return JSONRPCResponse(result=result, id=request.id)
            
            elif request.method == "tools/call":
                if not request.params:
                    return self._error_response(-32602, "Missing params", request.id)
                
                tool_name = request.params.get("name")
                arguments = request.params.get("arguments", {})
                
                if tool_name not in self._tools:
                    return self._error_response(-32601, f"Tool not found: {tool_name}", request.id)
                
                # Call the tool implementation
                result = await self.call_tool(tool_name, arguments)
                return JSONRPCResponse(result=result, id=request.id)
            
            elif request.method == "initialize":
                result = {
                    "protocolVersion": "0.1.0",
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.server_version,
                    },
                    "capabilities": self.get_capabilities(),
                }
                return JSONRPCResponse(result=result, id=request.id)
            
            else:
                return self._error_response(-32601, f"Method not found: {request.method}", request.id)
        
        except Exception as e:
            return self._error_response(-32603, f"Internal error: {str(e)}", request.id)
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given arguments.
        
        Must be implemented by subclasses.
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool input arguments
            
        Returns:
            Tool execution result
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return server capabilities.
        
        Must be implemented by subclasses.
        """
        pass
    
    def _error_response(
        self, code: int, message: str, request_id: Optional[str | int] = None, data: Any = None
    ) -> JSONRPCResponse:
        """Create JSON-RPC error response."""
        error = JSONRPCError(code=code, message=message, data=data)
        return JSONRPCResponse(error=error.model_dump(), id=request_id)
    
    async def start(self) -> None:
        """Start the MCP server."""
        pass
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        pass
