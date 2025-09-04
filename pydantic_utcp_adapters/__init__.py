# Package exports for pydantic_utcp_adapters

from .pydantic_tools import (
    PydanticAITool,
    load_utcp_tools_for_pydantic_ai,
    search_utcp_tools_for_pydantic_ai,
)

# Re-export LangChain adapter functions for convenience (optional)
from .langchain_tools import (
    convert_utcp_tool_to_langchain_tool,
    load_utcp_tools,
    search_utcp_tools,
)

__all__ = [
    # Pydantic adapters
    "PydanticAITool",
    "load_utcp_tools_for_pydantic_ai",
    "search_utcp_tools_for_pydantic_ai",
    # LangChain adapters
    "convert_utcp_tool_to_langchain_tool",
    "load_utcp_tools",
    "search_utcp_tools",
]
