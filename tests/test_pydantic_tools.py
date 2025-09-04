"""Tests for UTCP to PydanticAI tool conversion."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pydantic_utcp_adapters.pydantic_tools import (
    convert_utcp_tool_to_pydantic_ai,
    load_utcp_tools_for_pydantic_ai,
    search_utcp_tools_for_pydantic_ai,
    _convert_utcp_result,
    _create_pydantic_model_from_schema,
    _json_schema_to_python_type,
    PydanticAITool,
)

# Try to import UTCP types; if unavailable, provide minimal shims to unblock tests
try:  # pragma: no cover - environment-dependent
    from utcp.shared.tool import Tool as UTCPTool, JsonSchema  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without UTCP JsonSchema
    from dataclasses import dataclass, field
    
    class JsonSchema(dict):
        """Minimal dict-like schema with model_dump used by adapter/tests."""
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def model_dump(self, by_alias: bool = True, exclude_none: bool = True):
            # Provide a pydantic-like dump returning a plain dict
            return dict(self)

    @dataclass
    class UTCPTool:  # type: ignore
        name: str
        description: str = ""
        inputs: object | dict | None = None
        outputs: object | dict | None = None
        tags: list[str] = field(default_factory=list)
        tool_call_template: object | None = None

try:  # pragma: no cover - environment-dependent
    from utcp_http.http_call_template import HttpCallTemplate  # type: ignore
except Exception:  # pragma: no cover - fallback shim
    class HttpCallTemplate:  # type: ignore
        def __init__(self, name: str, call_template_type: str = "http", **kwargs):
            self.name = name
            self.call_template_type = call_template_type
            # store any other kwargs for completeness
            for k, v in kwargs.items():
                setattr(self, k, v)


class TestToolConversion:
    """Test UTCP to PydanticAI tool conversion."""

    def test_convert_utcp_result_string(self):
        """Test converting string result."""
        result = "Hello, world!"
        converted = _convert_utcp_result(result)
        assert converted == "Hello, world!"

    def test_convert_utcp_result_dict(self):
        """Test converting dictionary result."""
        result = {"message": "success", "data": [1, 2, 3]}
        converted = _convert_utcp_result(result)
        # Check that the JSON contains the expected content (formatting may vary)
        assert '"message"' in converted and '"success"' in converted
        assert '"data"' in converted and '1' in converted and '2' in converted and '3' in converted

    def test_convert_utcp_result_error(self):
        """Test converting error result."""
        result = {"error": "Something went wrong"}
        with pytest.raises(RuntimeError) as exc_info:
            _convert_utcp_result(result)
        assert "Something went wrong" in str(exc_info.value)

    def test_json_schema_to_python_type(self):
        """Test JSON schema to Python type conversion."""
        assert _json_schema_to_python_type({"type": "string"}) == str
        assert _json_schema_to_python_type({"type": "integer"}) == int
        assert _json_schema_to_python_type({"type": "number"}) == float
        assert _json_schema_to_python_type({"type": "boolean"}) == bool

    def test_create_pydantic_model_from_schema(self):
        """Test creating Pydantic model from JSON schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"}
            },
            "required": ["name", "age"]
        }
        
        model_class = _create_pydantic_model_from_schema(schema, "TestModel")
        
        # Test that required fields are properly set
        model_instance = model_class(name="John", age=30)
        assert model_instance.name == "John"
        assert model_instance.age == 30
        assert model_instance.email is None

    def test_create_pydantic_model_from_empty_schema(self):
        """Test creating Pydantic model from empty schema."""
        empty_schema = {"type": "object", "properties": {}}
        
        model_class = _create_pydantic_model_from_schema(empty_schema, "EmptyModel")
        
        # Test that the model can be created and accepts additional fields
        model_instance = model_class()
        assert model_instance is not None
        
        # Test that it can accept arbitrary keyword arguments
        model_instance_with_data = model_class(arbitrary_field="test")
        assert model_instance_with_data.arbitrary_field == "test"

    def test_create_pydantic_model_from_malformed_schema(self):
        """Test creating Pydantic model from malformed schema."""
        malformed_schema = {"properties": None, "required": "not_a_list"}
        
        model_class = _create_pydantic_model_from_schema(malformed_schema, "MalformedModel")
        
        # Should create a flexible model that doesn't crash
        model_instance = model_class()
        assert model_instance is not None

    def test_pydantic_ai_tool_metadata(self):
        """Test PydanticAITool metadata extraction."""
        provider = HttpCallTemplate(
            name="test_provider",
            call_template_type="http",
            url="http://example.com/api",
            http_method="POST"
        )
        
        utcp_tool = UTCPTool(
            name="test_provider.test_tool",
            description="A test tool",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=["test", "example"],
            tool_call_template=provider
        )
        
        mock_client = AsyncMock()
        pydantic_tool = PydanticAITool(mock_client, utcp_tool)
        
        # Test metadata extraction
        metadata = pydantic_tool.get_metadata()
        assert metadata["manual_name"] == "test_provider"
        assert metadata["call_template"] == "test_provider"
        assert metadata["call_template_type"] == "http"
        assert metadata["tags"] == ["test", "example"]
        assert metadata["utcp_tool"] is True

    def test_tool_name_without_namespace(self):
        """Test tool name handling for tools without namespace (edge case)."""
        provider = HttpCallTemplate(
            name="test_provider",
            call_template_type="http",
            url="http://example.com/api",
            http_method="POST"
        )
        
        # Create a tool without namespace (edge case)
        utcp_tool = UTCPTool(
            name="standalone_tool",  # No namespace
            description="A standalone tool",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider
        )
        
        mock_client = AsyncMock()
        pydantic_tool = PydanticAITool(mock_client, utcp_tool)
        
        # Should handle gracefully
        assert pydantic_tool.name == "standalone_tool"
        metadata = pydantic_tool.get_metadata()
        assert metadata["manual_name"] == "unknown"  # Fallback for no namespace
        assert metadata["call_template"] == "unknown"  # Fallback for backward compatibility

    @pytest.mark.asyncio
    async def test_convert_utcp_tool_to_pydantic_ai(self):
        """Test converting UTCP tool to PydanticAI tool."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"result": "success"}
        
        # Create UTCP tool
        provider = HttpCallTemplate(
            name="test_provider",
            call_template_type="http",
            url="http://example.com/api",
            http_method="POST"
        )
        
        utcp_tool = UTCPTool(
            name="test_provider.test_tool",  # Use namespaced name as UTCP would provide
            description="A test tool",
            inputs=JsonSchema(
                type="object",
                properties={
                    "input_text": JsonSchema(type="string")
                },
                required=["input_text"]
            ),
            outputs=JsonSchema(
                type="object",
                properties={
                    "output_text": JsonSchema(type="string")
                }
            ),
            tags=["test"],
            tool_call_template=provider
        )
        
        # Convert to PydanticAI tool
        pydantic_tool = convert_utcp_tool_to_pydantic_ai(mock_client, utcp_tool)
        
        # Test tool properties
        assert pydantic_tool.name == "test_provider.test_tool"  # UTCP provides namespaced names
        assert pydantic_tool.description == "A test tool"
        metadata = pydantic_tool.get_metadata()
        assert metadata["call_template"] == "test_provider"  # Extracted from tool name
        assert metadata["manual_name"] == "test_provider"  # New explicit field
        assert metadata["call_template_type"] == "http"
        assert metadata["utcp_tool"] is True
        
        # Test tool execution
        result = await pydantic_tool(input_text="hello")
        assert "success" in result
        mock_client.call_tool.assert_called_once_with(
            "test_provider.test_tool",  # UTCP uses the namespaced tool name
            {"input_text": "hello"}
        )

    @pytest.mark.asyncio
    async def test_pydantic_ai_tool_execution_error(self):
        """Test PydanticAI tool execution with error."""
        mock_client = AsyncMock()
        mock_client.call_tool.side_effect = Exception("Tool execution failed")
        
        provider = HttpCallTemplate(
            name="test_provider",
            call_template_type="http",
            url="http://example.com/api",
            http_method="POST"
        )
        
        utcp_tool = UTCPTool(
            name="test_provider.error_tool",
            description="A tool that errors",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider
        )
        
        pydantic_tool = PydanticAITool(mock_client, utcp_tool)
        
        # Test that error is properly wrapped
        with pytest.raises(RuntimeError) as exc_info:
            await pydantic_tool()
        
        assert "Error calling UTCP tool test_provider.error_tool" in str(exc_info.value)
        assert "Tool execution failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_utcp_tools_for_pydantic_ai(self):
        """Test loading UTCP tools for PydanticAI."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        
        # Create mock call template
        provider = HttpCallTemplate(name="test_provider", call_template_type="http", url="http://example.com")
        
        utcp_tool = UTCPTool(
            name="test_provider.test_tool",  # Use namespaced name
            description="A test tool",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider
        )
        
        # Mock the search_tools method that load_utcp_tools_for_pydantic_ai actually uses
        mock_client.search_tools.return_value = [utcp_tool]
        
        # Load tools
        pydantic_tools = await load_utcp_tools_for_pydantic_ai(mock_client)
        
        # Verify results
        assert len(pydantic_tools) == 1
        assert isinstance(pydantic_tools[0], PydanticAITool)
        assert pydantic_tools[0].name == "test_provider.test_tool"
        metadata = pydantic_tools[0].get_metadata()
        assert metadata["utcp_tool"] is True
        
        # Verify search_tools was called with empty string and high limit
        mock_client.search_tools.assert_called_once_with("", limit=1000)

    @pytest.mark.asyncio
    async def test_load_utcp_tools_for_pydantic_ai_with_call_template_filter(self):
        """Test loading UTCP tools with call template filter."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        
        # Create mock call templates
        provider1 = HttpCallTemplate(name="provider1", call_template_type="http", url="http://example1.com")
        provider2 = HttpCallTemplate(name="provider2", call_template_type="http", url="http://example2.com")
        
        tool1 = UTCPTool(
            name="provider1.tool1",  # Use namespaced name
            description="Tool 1",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider1
        )
        
        tool2 = UTCPTool(
            name="provider2.tool2",  # Use namespaced name
            description="Tool 2",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider2
        )
        
        # Mock search_tools to return both tools
        mock_client.search_tools.return_value = [tool1, tool2]
        
        # Load tools with call template filter
        pydantic_tools = await load_utcp_tools_for_pydantic_ai(mock_client, call_template_name="provider1")
        
        # Verify only provider1 tools are returned
        assert len(pydantic_tools) == 1
        assert pydantic_tools[0].name == "provider1.tool1"

    @pytest.mark.asyncio
    async def test_load_utcp_tools_for_pydantic_ai_error_handling(self):
        """Test load tools error handling."""
        # Create mock UTCP client that fails
        mock_client = AsyncMock()
        mock_client.search_tools.side_effect = Exception("Search failed")
        
        # Load tools - should return empty list gracefully
        pydantic_tools = await load_utcp_tools_for_pydantic_ai(mock_client)
        
        # Verify graceful failure
        assert len(pydantic_tools) == 0

    @pytest.mark.asyncio
    async def test_search_utcp_tools_for_pydantic_ai(self):
        """Test searching UTCP tools for PydanticAI."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        
        provider = HttpCallTemplate(name="test_provider", call_template_type="http", url="http://example.com")
        utcp_tool = UTCPTool(
            name="test_provider.search_tool",  # Use namespaced name
            description="A searchable tool",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider
        )
        
        mock_client.search_tools.return_value = [utcp_tool]
        
        # Search tools
        pydantic_tools = await search_utcp_tools_for_pydantic_ai(mock_client, "search query")
        
        # Verify results
        assert len(pydantic_tools) == 1
        assert isinstance(pydantic_tools[0], PydanticAITool)
        assert pydantic_tools[0].name == "test_provider.search_tool"
        mock_client.search_tools.assert_called_once_with("search query", limit=1000)

    @pytest.mark.asyncio
    async def test_search_utcp_tools_for_pydantic_ai_with_max_results(self):
        """Test searching UTCP tools with max results limit."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        
        provider = HttpCallTemplate(name="test_provider", call_template_type="http", url="http://example.com")
        utcp_tool = UTCPTool(
            name="test_provider.search_tool",
            description="A searchable tool",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider
        )
        
        mock_client.search_tools.return_value = [utcp_tool]
        
        # Search tools with max results
        pydantic_tools = await search_utcp_tools_for_pydantic_ai(
            mock_client, "search query", max_results=5
        )
        
        # Verify results
        assert len(pydantic_tools) == 1
        mock_client.search_tools.assert_called_once_with("search query", limit=5)

    @pytest.mark.asyncio
    async def test_search_utcp_tools_for_pydantic_ai_with_fallback(self):
        """Test search tools fallback logic when primary search fails."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        
        provider = HttpCallTemplate(name="test_provider", call_template_type="http", url="http://example.com")
        
        utcp_tool = UTCPTool(
            name="test_provider.fallback_tool",
            description="A tool for fallback testing",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=["fallback"],
            tool_call_template=provider
        )
        
        # Mock the primary search to fail, but empty search to succeed
        def mock_search_side_effect(query, limit):
            if query == "fallback":
                raise Exception("Primary search failed")
            elif query == "":
                return [utcp_tool]  # Empty search succeeds
            else:
                return []
        
        mock_client.search_tools.side_effect = mock_search_side_effect
        
        # Search tools - should trigger fallback
        pydantic_tools = await search_utcp_tools_for_pydantic_ai(mock_client, "fallback")
        
        # Verify fallback worked
        assert len(pydantic_tools) == 1
        assert pydantic_tools[0].name == "test_provider.fallback_tool"
        
        # Verify both calls were made (primary + fallback)
        assert mock_client.search_tools.call_count == 2
        mock_client.search_tools.assert_any_call("fallback", limit=1000)  # Primary call
        mock_client.search_tools.assert_any_call("", limit=1000)  # Fallback call

    @pytest.mark.asyncio
    async def test_search_utcp_tools_for_pydantic_ai_complete_failure(self):
        """Test search tools when all methods fail."""
        # Create mock UTCP client that always fails
        mock_client = AsyncMock()
        mock_client.search_tools.side_effect = Exception("All search methods failed")
        
        # Mock load_utcp_tools_for_pydantic_ai to also fail
        with patch('pydantic_utcp_adapters.pydantic_tools.load_utcp_tools_for_pydantic_ai') as mock_load:
            mock_load.side_effect = Exception("Load also failed")
            
            # Search tools - should return empty list
            pydantic_tools = await search_utcp_tools_for_pydantic_ai(mock_client, "test query")
            
            # Verify graceful failure
            assert len(pydantic_tools) == 0

    @pytest.mark.asyncio
    async def test_search_utcp_tools_for_pydantic_ai_with_call_template_filter(self):
        """Test searching UTCP tools with call template filter."""
        # Create mock UTCP client
        mock_client = AsyncMock()
        
        # Create mock call templates
        provider1 = HttpCallTemplate(name="provider1", call_template_type="http", url="http://example1.com")
        provider2 = HttpCallTemplate(name="provider2", call_template_type="http", url="http://example2.com")
        
        tool1 = UTCPTool(
            name="provider1.search_tool",
            description="Search tool 1",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=["search"],
            tool_call_template=provider1
        )
        
        tool2 = UTCPTool(
            name="provider2.search_tool",
            description="Search tool 2",
            inputs=JsonSchema(type="object", properties={}),
            outputs=JsonSchema(type="object", properties={}),
            tags=["search"],
            tool_call_template=provider2
        )
        
        # Mock search_tools to return both tools
        mock_client.search_tools.return_value = [tool1, tool2]
        
        # Search tools with call template filter
        pydantic_tools = await search_utcp_tools_for_pydantic_ai(
            mock_client, "search", call_template_name="provider1"
        )
        
        # Verify only provider1 tools are returned
        assert len(pydantic_tools) == 1
        assert pydantic_tools[0].name == "provider1.search_tool"

    def test_pydantic_ai_tool_input_schema(self):
        """Test PydanticAI tool input schema generation."""
        provider = HttpCallTemplate(
            name="test_provider",
            call_template_type="http",
            url="http://example.com/api",
            http_method="POST"
        )
        
        utcp_tool = UTCPTool(
            name="test_provider.schema_tool",
            description="A tool with complex schema",
            inputs=JsonSchema(
                type="object",
                properties={
                    "name": JsonSchema(type="string"),
                    "age": JsonSchema(type="integer"),
                    "active": JsonSchema(type="boolean")
                },
                required=["name"]
            ),
            outputs=JsonSchema(type="object", properties={}),
            tags=[],
            tool_call_template=provider
        )
        
        mock_client = AsyncMock()
        pydantic_tool = PydanticAITool(mock_client, utcp_tool)
        
        # Test input schema generation
        schema = pydantic_tool.get_input_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "active" in schema["properties"]
        assert schema["required"] == ["name"]
