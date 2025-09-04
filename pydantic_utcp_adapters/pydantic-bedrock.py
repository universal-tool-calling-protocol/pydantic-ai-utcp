"""
Bedrock-specific utilities for PydanticAI UTCP Adapters.

This module provides utilities for formatting UTCP tools wrapped as PydanticAITool
instances to work with Amazon Bedrock's strict tool naming requirements.
"""

import uuid
from typing import Dict, List, Tuple, Any, Optional

from .pydantic_tools import PydanticAITool


def format_tool_name_for_bedrock(tool_name: str) -> str:
    """
    Format a tool name to meet Bedrock's requirements.
    
    Bedrock requires tool names to:
    - Be 64 characters or less
    - Match pattern ^[a-zA-Z0-9_-]{1,64}$
    
    Args:
        tool_name: Original tool name
        
    Returns:
        Formatted tool name that meets Bedrock requirements
    """
    # Replace periods with underscores (common in UTCP tool names)
    bedrock_name = tool_name.replace(".", "_")
    
    # Remove any other invalid characters and replace with underscores
    valid_chars = []
    for char in bedrock_name:
        if char.isalnum() or char in ['_', '-']:
            valid_chars.append(char)
        else:
            valid_chars.append('_')
    
    bedrock_name = ''.join(valid_chars)
    
    # Truncate if longer than 64 characters
    if len(bedrock_name) > 64:
        # Use first 55 chars + underscore + 8-char UUID
        short_uuid = str(uuid.uuid4()).replace('-', '')[:8]
        bedrock_name = f"{bedrock_name[:55]}_{short_uuid}"
    
    return bedrock_name


class BedrockCompatiblePydanticTool(PydanticAITool):
    """
    A wrapper that provides Bedrock-compatible naming while preserving
    all original PydanticAITool functionality.
    """

    def __init__(self, original_tool: PydanticAITool, bedrock_name: str):
        # Copy original attributes
        # We intentionally do not call super().__init__ because we already have a wrapped tool
        self._original_tool = original_tool
        self.utcp_client = original_tool.utcp_client
        self.tool = original_tool.tool
        self.name = bedrock_name
        self.description = original_tool.description
        self.input_model = original_tool.input_model

    async def __call__(self, **kwargs: Any) -> Any:
        # Delegate to original tool
        return await self._original_tool(**kwargs)

    def get_input_schema(self) -> Dict[str, Any]:
        return self._original_tool.get_input_schema()

    @property
    def original_name(self) -> str:
        return self._original_tool.name

    @property
    def original_tool(self) -> PydanticAITool:
        return self._original_tool


def create_bedrock_tool_mapping_for_pydantic(
    tools: List[PydanticAITool],
) -> Tuple[List[PydanticAITool], Dict[str, str]]:
    """
    Create Bedrock-compatible PydanticAI tools with name mapping.
    
    Args:
        tools: List of PydanticAITool with potentially incompatible names
        
    Returns:
        Tuple of (tools_with_bedrock_names, mapping_bedrock_to_original)
    """
    bedrock_tools: List[PydanticAITool] = []
    name_mapping: Dict[str, str] = {}

    for tool in tools:
        original_name = tool.name
        bedrock_name = format_tool_name_for_bedrock(original_name)
        name_mapping[bedrock_name] = original_name

        if bedrock_name == original_name:
            bedrock_tools.append(tool)
        else:
            bedrock_tools.append(BedrockCompatiblePydanticTool(tool, bedrock_name))

    return bedrock_tools, name_mapping


def restore_original_tool_names(
    tool_calls: List[Dict],
    name_mapping: Dict[str, str],
) -> List[Dict]:
    """
    Restore original tool names in tool calls from Bedrock.
    This is useful when reconciling Bedrock outputs back to UTCP tool names.
    
    Args:
        tool_calls: List of tool calls with Bedrock names (dicts containing 'name')
        name_mapping: Mapping from Bedrock names to original names
        
    Returns:
        List of tool calls with original names restored
    """
    restored: List[Dict] = []
    for call in tool_calls:
        restored_call = dict(call)
        if 'name' in restored_call and restored_call['name'] in name_mapping:
            restored_call['name'] = name_mapping[restored_call['name']]
        restored.append(restored_call)
    return restored
