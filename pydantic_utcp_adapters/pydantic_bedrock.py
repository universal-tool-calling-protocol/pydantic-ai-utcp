"""
Bedrock-specific utilities for Pydantic UTCP Adapters.

This module provides utilities for formatting UTCP tools to work with Amazon Bedrock's
strict tool naming requirements when using Pydantic models.
"""

import uuid
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


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


def create_bedrock_tool_mapping(tool_models: List[Type[BaseModel]]) -> Dict[str, str]:
    """
    Create a mapping from Bedrock-compatible names to original tool model names.
    
    Args:
        tool_models: List of Pydantic models representing tools
        
    Returns:
        Mapping from Bedrock names to original model names
    """
    name_mapping = {}
    
    for model in tool_models:
        original_name = model.__name__
        bedrock_name = format_tool_name_for_bedrock(original_name)
        name_mapping[bedrock_name] = original_name
    
    return name_mapping


class BedrockCompatibleModel(Generic[T]):
    """
    A wrapper for Pydantic models that provides Bedrock-compatible naming
    while preserving the original model structure.
    """
    
    def __init__(self, original_model: Type[T], bedrock_name: str):
        """
        Initialize the Bedrock-compatible model wrapper.
        
        Args:
            original_model: The original Pydantic model
            bedrock_name: The Bedrock-compatible name
        """
        self.original_model = original_model
        self.bedrock_name = bedrock_name
        
        # Create a new model with the Bedrock-compatible name
        self.model = create_model(
            bedrock_name,
            __base__=original_model,
            __module__=original_model.__module__,
            __doc__=original_model.__doc__
        )
    
    def __call__(self, *args, **kwargs) -> T:
        """Create an instance of the original model."""
        return self.original_model(*args, **kwargs)
    
    def model_validate(self, obj: Any, **kwargs) -> T:
        """Validate and parse the input data using the original model."""
        return self.original_model.model_validate(obj, **kwargs)
    
    def model_validate_json(self, json_data: str, **kwargs) -> T:
        """Validate and parse JSON data using the original model."""
        return self.original_model.model_validate_json(json_data, **kwargs)
    
    @property
    def __name__(self) -> str:
        """Return the Bedrock-compatible name."""
        return self.bedrock_name
    
    @property
    def __pydantic_core_schema__(self):
        """Delegate to the original model's schema."""
        return self.original_model.__pydantic_core_schema__


def restore_original_tool_names(tool_calls: List[Dict], name_mapping: Dict[str, str]) -> List[Dict]:
    """
    Restore original tool names in tool calls from Bedrock.
    
    Args:
        tool_calls: List of tool calls with Bedrock names
        name_mapping: Mapping from Bedrock names to original names
        
    Returns:
        List of tool calls with original names restored
    """
    restored_calls = []
    
    for call in tool_calls:
        restored_call = call.copy()
        
        # Restore the original name if it exists in mapping
        if 'name' in restored_call and restored_call['name'] in name_mapping:
            restored_call['name'] = name_mapping[restored_call['name']]
        
        restored_calls.append(restored_call)
    
    return restored_calls
