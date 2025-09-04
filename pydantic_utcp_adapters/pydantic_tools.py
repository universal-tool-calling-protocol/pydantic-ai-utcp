"""Tools adapter for converting UTCP tools to PydanticAI tools.

This module provides functionality to convert UTCP tools into PydanticAI-compatible
wrappers, handle tool execution, and manage loading/searching tools.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, create_model, ConfigDict
from utcp.client.utcp_client import UtcpClient
from utcp.shared.tool import Tool as UTCPTool

# Configure logger for this module
logger = logging.getLogger(__name__)


def _convert_utcp_result(result: Any) -> str:
    """Convert UTCP tool result to PydanticAI tool result format.

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
    if not isinstance(schema, dict):
        return str

    schema_type = schema.get("type", "string")

    if schema_type is None:
        schema_type = "string"

    if schema_type == "array":
        items_schema = schema.get("items", {"type": "string"})
        if isinstance(items_schema, dict):
            item_type = _json_schema_to_python_type(items_schema)
            from typing import List as TList  # avoid shadowing
            return TList[item_type]  # type: ignore[index]
        else:
            from typing import List as TList
            return TList[Any]  # type: ignore[index]

    if "anyOf" in schema or "oneOf" in schema:
        return Any

    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": List[Any],  # fallback
        "object": Dict[str, Any],
        "null": type(None),
    }
    return mapping.get(schema_type, str)


def _create_pydantic_model_from_schema(
    schema: Dict[str, Any],
    model_name: str = "ToolInput",
) -> Type[BaseModel]:
    """Create a Pydantic model from a JSON schema.

    Args:
        schema: JSON schema dictionary (from UTCP JsonSchema object)
        model_name: Name for the generated model

    Returns:
        A Pydantic BaseModel class
    """
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = schema.get("required", []) if isinstance(schema, dict) else []

    if not isinstance(properties, dict):
        properties = {}
    if not isinstance(required, list):
        required = []

    # If primitive schema without properties
    if not properties and schema.get("type") not in [None, "object"]:
        field_type = _json_schema_to_python_type({"type": schema.get("type", "string")})
        return create_model(model_name, value=(field_type, ...))

    field_defs: Dict[str, tuple[type, Any]] = {}

    from typing import Optional as TOptional  # to annotate optional types dynamically

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
        f_type = _json_schema_to_python_type(field_schema)
        if field_name in required:
            default = ...
        else:
            f_type = TOptional[f_type]  # type: ignore[index]
            default = None
        field_defs[field_name] = (f_type, default)

    if not field_defs:
        # Flexible model allowing any extra fields
        class FlexibleModel(BaseModel):
            model_config = ConfigDict(extra="allow")
        FlexibleModel.__name__ = model_name
        return FlexibleModel

    return create_model(model_name, **field_defs)


class PydanticAITool:
    """Wrapper for UTCP tools to be used with PydanticAI or generic async usage."""

    def __init__(self, utcp_client: UtcpClient, tool: UTCPTool):
        self.utcp_client = utcp_client
        self.tool = tool
        self.name = tool.name
        self.description = tool.description or f"UTCP tool: {tool.name}"

        # Build input model from UTCP JsonSchema/Pydantic model
        if hasattr(tool.inputs, "model_dump"):
            schema_dict = tool.inputs.model_dump(by_alias=True, exclude_none=True)
        elif hasattr(tool.inputs, "__dict__"):
            schema_dict = tool.inputs.__dict__
        elif isinstance(tool.inputs, dict):
            schema_dict = tool.inputs
        else:
            schema_dict = {"type": "object", "properties": {}}

        self.input_model = _create_pydantic_model_from_schema(
            schema_dict, f"{tool.name.replace('.', '_')}Input"
        )
        
        # Extract metadata similar to langchain version
        manual_name = tool.name.split('.')[0] if '.' in tool.name else "unknown"
        
        # Get call template type from the tool's call template with proper validation
        call_template_type = "unknown"
        if (hasattr(tool, 'tool_call_template') and 
            tool.tool_call_template is not None and 
            hasattr(tool.tool_call_template, 'call_template_type')):
            call_template_type = tool.tool_call_template.call_template_type
        
        self.metadata = {
            "manual_name": manual_name,
            "call_template": manual_name,
            "call_template_type": call_template_type,
            "tags": tool.tags,
            "utcp_tool": True,
        }

    async def __call__(self, **kwargs: Any) -> Any:
        try:
            validated = self.input_model(**kwargs).model_dump()
            result = await self.utcp_client.call_tool(self.tool.name, validated)
            return _convert_utcp_result(result)
        except Exception as e:
            raise RuntimeError(f"Error calling UTCP tool {self.tool.name}: {e}") from e

    def get_input_schema(self) -> Dict[str, Any]:
        """Get the input schema for this tool."""
        return self.input_model.model_json_schema()
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for this tool."""
        return self.metadata


def convert_utcp_tool_to_pydantic_ai(
    utcp_client: UtcpClient,
    tool: UTCPTool,
) -> PydanticAITool:
    """Convert a UTCP tool to a PydanticAI tool.

    Args:
        utcp_client: UTCP client instance for tool execution
        tool: UTCP tool to convert

    Returns:
        A PydanticAI tool wrapper
    """
    return PydanticAITool(utcp_client, tool)


async def load_utcp_tools_for_pydantic_ai(
    utcp_client: UtcpClient,
    call_template_name: Optional[str] = None,
) -> List[PydanticAITool]:
    """Load all available UTCP tools and convert them to PydanticAI tools.

    Args:
        utcp_client: The UTCP client instance
        call_template_name: Optional call template name to filter tools

    Returns:
        List of PydanticAI tools
    """
    try:
        # Get all tools from the UTCP client using search with empty string and high limit
        all_tools = await utcp_client.search_tools("", limit=1000)
    except Exception as e:
        logger.error("Failed to load tools from UTCP client: %s", e)
        return []
    
    # Filter by call template if specified
    if call_template_name:
        # Improved filtering with better null checks
        filtered_tools = []
        for tool in all_tools:
            if (hasattr(tool, 'tool_call_template') and 
                tool.tool_call_template is not None and
                hasattr(tool.tool_call_template, 'name')):
                
                # Extract manual name from tool name for comparison
                tool_manual_name = tool.name.split('.')[0] if '.' in tool.name else "unknown"
                
                if tool_manual_name == call_template_name:
                    filtered_tools.append(tool)
        
        all_tools = filtered_tools
    
    # Convert each UTCP tool to a PydanticAI tool
    pydantic_tools = []
    for utcp_tool in all_tools:
        try:
            pydantic_tool = convert_utcp_tool_to_pydantic_ai(utcp_client, utcp_tool)
            pydantic_tools.append(pydantic_tool)
        except Exception as e:
            # Log the error but continue with other tools
            logger.warning("Failed to convert tool %s: %s", utcp_tool.name, e)
    
    return pydantic_tools


async def search_utcp_tools_for_pydantic_ai(
    utcp_client: UtcpClient,
    query: str,
    call_template_name: Optional[str] = None,
    max_results: Optional[int] = None,
) -> List[PydanticAITool]:
    """Search for UTCP tools and convert them to PydanticAI tools.

    Args:
        utcp_client: The UTCP client instance
        query: Search query string
        call_template_name: Optional call template name to filter tools
        max_results: Maximum number of results to return

    Returns:
        List of relevant PydanticAI tools
    """
    search_results = []
    
    # Try UTCP's built-in search functionality first
    try:
        limit = max_results if max_results is not None else 1000
        search_results = await utcp_client.search_tools(query, limit=limit)
    except Exception as e:
        logger.warning("UTCP search failed (%s), attempting fallback methods", e)
        
        # Fallback 1: Try to get all tools with empty query (sometimes works when specific queries fail)
        try:
            logger.info("Trying to get all tools with empty query...")
            all_tools = await utcp_client.search_tools("", limit=1000)
            
            # Manually filter the results
            query_lower = query.lower()
            search_results = []
            
            for tool in all_tools:
                # Search in name, description, and tags
                if (query_lower in tool.name.lower() or 
                    query_lower in tool.description.lower() or
                    any(query_lower in tag.lower() for tag in tool.tags)):
                    search_results.append(tool)
            
            logger.info("Fallback search found %d matching tools", len(search_results))
            
        except Exception as e2:
            logger.warning("Fallback search also failed (%s)", e2)
            
            # Fallback 2: Try to use load_utcp_tools_for_pydantic_ai and filter manually
            try:
                logger.info("Trying to load all tools via load_utcp_tools_for_pydantic_ai...")
                # Use the load function which might have different error handling
                all_pydantic_tools = await load_utcp_tools_for_pydantic_ai(utcp_client, call_template_name)
                
                # Filter the PydanticAI tools by query
                query_lower = query.lower()
                filtered_tools = []
                
                for tool in all_pydantic_tools:
                    if (query_lower in tool.name.lower() or 
                        query_lower in tool.description.lower() or
                        any(query_lower in tag.lower() for tag in tool.metadata.get("tags", []))):
                        filtered_tools.append(tool)
                
                # Apply max_results limit if specified
                if max_results:
                    filtered_tools = filtered_tools[:max_results]
                
                logger.info("Final fallback found %d matching tools", len(filtered_tools))
                return filtered_tools
                
            except Exception as e3:
                logger.error("All fallback methods failed (%s). Returning empty list.", e3)
                return []
    
    # Apply max_results limit if specified (for successful search)
    if max_results and len(search_results) > max_results:
        search_results = search_results[:max_results]
    
    # Filter by call template if specified
    if call_template_name:
        search_results = [
            tool for tool in search_results 
            if hasattr(tool, 'tool_call_template') and 
               tool.tool_call_template is not None and
               hasattr(tool.tool_call_template, 'name') and 
               tool.tool_call_template.name == call_template_name
        ]
    
    # Convert each UTCP tool to a PydanticAI tool
    pydantic_tools = []
    for utcp_tool in search_results:
        try:
            pydantic_tool = convert_utcp_tool_to_pydantic_ai(utcp_client, utcp_tool)
            pydantic_tools.append(pydantic_tool)
        except Exception as e:
            # Log the error but continue with other tools
            logger.warning("Failed to convert tool %s: %s", utcp_tool.name, e)
    
    return pydantic_tools
