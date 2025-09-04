"""Tools adapter for converting UTCP tools to PydanticAI tools.

This module provides functionality to convert UTCP tools into PydanticAI-compatible
tools, handle tool execution, and manage tool conversion between the two formats.
"""

import json
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, create_model
from utcp.client.utcp_client import UtcpClient
from utcp.shared.tool import Tool as UTCPTool

def _convert_utcp_result(result: Any) -> str:
    """Convert UTCP tool result to string format.

    Args:
        result: The result from calling a UTCP tool.

    Returns:
        A string representation of the result.
    
    Raises:
        RuntimeError: If the tool call resulted in an error.
    """
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(str(result["error"]))
    
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2)
    
    return str(result)

def _json_schema_to_python_type(schema: Dict[str, Any]) -> Type:
    """Convert JSON schema type to Python type.

    Args:
        schema: JSON schema for a field

    Returns:
        Python type corresponding to the schema
    """
    schema_type = schema.get("type", "string")

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": List[Any],
        "object": Dict[str, Any],
    }

    return type_mapping.get(schema_type, Any)

def _create_pydantic_model_from_schema(
    schema: Dict[str, Any],
    model_name: str = "ToolInput"
) -> Type[BaseModel]:
    """Create a Pydantic model from a JSON schema.

    Args:
        schema: JSON schema dictionary
        model_name: Name for the generated model

    Returns:
        A Pydantic BaseModel class
    """
    if schema.get("type") != "object":
        return create_model(model_name, value=(Any, ...))
    
    properties = schema.get("properties", {})
    required = schema.get("required") or []
    
    field_definitions = {}
    
    for field_name, field_schema in properties.items():
        field_type = _json_schema_to_python_type(field_schema)
        default_value = ... if field_name in required else None
        field_definitions[field_name] = (field_type, default_value)
    
    if not field_definitions:
        field_definitions["_empty"] = (Optional[str], None)
    
    return create_model(model_name, **field_definitions)

class PydanticAITool:
    """Wrapper for UTCP tools to be used with PydanticAI.
    """
    def __init__(self, utcp_client: UtcpClient, tool: UTCPTool):
        self.utcp_client = utcp_client
        self.tool = tool
        self.name = tool.name
        self.description = tool.description
        self.input_model = _create_pydantic_model_from_schema(
            tool.inputs.model_dump() if hasattr(tool.inputs, 'model_dump') else tool.inputs.__dict__,
            f"{tool.name.replace('.', '_')}Input"
        )

    async def __call__(self, **kwargs: Any) -> Any:
        """Execute the UTCP tool.
        """
        try:
            validated_args = self.input_model(**kwargs).model_dump()
            result = await self.utcp_client.call_tool(self.tool.name, validated_args)
            return _convert_utcp_result(result)
        except Exception as e:
            raise RuntimeError(f"Error calling UTCP tool {self.tool.name}: {str(e)}") from e

    def get_input_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool's input.
        """
        return self.input_model.model_json_schema()

async def load_utcp_tools_for_pydantic_ai(
    utcp_client: UtcpClient,
    provider_name: Optional[str] = None,
) -> List[PydanticAITool]:
    """Load all available UTCP tools and wrap them for PydanticAI.

    Args:
        utcp_client: The UTCP client instance
        provider_name: Optional provider name to filter tools

    Returns:
        List of PydanticAITool instances
    """
    all_tools = await utcp_client.tool_repository.get_tools()
    
    if provider_name:
        all_tools = [
            tool for tool in all_tools 
            if tool.tool_provider.name == provider_name
        ]
    
    pydantic_ai_tools = []
    for utcp_tool in all_tools:
        try:
            pydantic_ai_tools.append(PydanticAITool(utcp_client, utcp_tool))
        except Exception as e:
            print(f"Warning: Failed to wrap tool {utcp_tool.name} for PydanticAI: {e}")
    
    return pydantic_ai_tools

async def search_utcp_tools_for_pydantic_ai(
    utcp_client: UtcpClient,
    query: str,
    provider_name: Optional[str] = None,
    max_results: Optional[int] = None,
) -> List[PydanticAITool]:
    """Search for UTCP tools and wrap them for PydanticAI.

    Args:
        utcp_client: The UTCP client instance
        query: Search query string
        provider_name: Optional provider name to filter tools
        max_results: Maximum number of results to return

    Returns:
        List of relevant PydanticAITool instances
    """
    try:
        search_results = await utcp_client.search_tools(query)
    except Exception as e:
        print(f"Warning: UTCP search failed ({e}), falling back to manual search")
        all_tools = await utcp_client.tool_repository.get_tools()
        query_lower = query.lower()
        
        search_results = []
        for tool in all_tools:
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                search_results.append(tool)
    
    if provider_name:
        search_results = [
            tool for tool in search_results 
            if tool.tool_provider.name == provider_name
        ]
    
    if max_results:
        search_results = search_results[:max_results]
    
    pydantic_ai_tools = []
    for utcp_tool in search_results:
        try:
            pydantic_ai_tools.append(PydanticAITool(utcp_client, utcp_tool))
        except Exception as e:
            print(f"Warning: Failed to wrap tool {utcp_tool.name} for PydanticAI: {e}")
    
    return pydantic_ai_tools