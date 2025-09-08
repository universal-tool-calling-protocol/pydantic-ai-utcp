#!/usr/bin/env python3
"""Test script for PydanticAI UTCP Adapters with real providers.

This script tests the package with actual UTCP providers to validate
that real tools are loaded and working correctly (Pydantic version).
"""
import json
import asyncio
import pytest
from utcp.utcp_client import UtcpClient
from pydantic_utcp_adapters import (
    load_utcp_tools_for_pydantic_ai,
    search_utcp_tools_for_pydantic_ai,
)


@pytest.mark.asyncio
async def test_real_providers():
    """Test with real UTCP providers to validate functionality (Pydantic)."""
    print('🧪 Testing PydanticAI UTCP Adapters with Real Providers')
    print('=' * 60)

    try:
        # Create UTCP client directly (UTCP 1.0 style configuration)
        print('📡 Creating UTCP client...')
        config = {
            "tool_repository": {"tool_repository_type": "in_memory"},
            "tool_search_strategy": {"tool_search_strategy_type": "tag_and_description_word_match"},
            "manual_call_templates": [
                {
                    "name": "openlibrary",
                    "call_template_type": "http",
                    "http_method": "GET",
                    "url": "https://openlibrary.org/static/openapi.json",
                    "content_type": "application/json",
                }
            ],
        }
        client = await UtcpClient.create(config=config)
        print('✅ Client created successfully')

        # Load tools
        print('\n🔧 Loading tools...')
        tools = await load_utcp_tools_for_pydantic_ai(client)
        print(f'✅ Successfully loaded {len(tools)} tools')

        # Validate tools
        assert len(tools) > 0, "Should have loaded at least one tool"

        # Check tool properties
        for tool in tools[:3]:  # Check first 3 tools
            print(f'  📖 Tool: {tool.name}')
            print(f'     Description: {tool.description}')
            print(f'     Input Model: {tool.input_model.__name__}')
            print(f'     Metadata: manual={tool.metadata.get("manual_name", "unknown")}, '
                  f'call_template_type={tool.metadata.get("call_template_type", "unknown")}')

            # Validate tool has required properties
            assert hasattr(tool, 'name'), "Tool should have name"
            assert hasattr(tool, 'description'), "Tool should have description"
            assert hasattr(tool, 'input_model'), "Tool should have input_model"
            assert tool.metadata.get('utcp_tool') is True, "Tool should be marked as UTCP tool"

        # Test search functionality
        print('\n🔍 Testing search functionality...')
        search_results = await search_utcp_tools_for_pydantic_ai(client, "books", max_results=3)
        print(f'✅ Search returned {len(search_results)} results')

        # Validate search results
        for tool in search_results:
            print(f'  🔎 Found: {tool.name}')
            name_ok = 'books' in tool.name.lower()
            desc_ok = 'books' in (tool.description or '').lower()
            tags = tool.metadata.get('tags', []) or []
            tags_ok = any('books' in (tag or '').lower() for tag in tags)
            assert name_ok or desc_ok or tags_ok, \
                "Search result should be related to 'books'"

        print('\n🎉 All tests passed successfully!')
        return True

    except Exception as e:
        print(f'❌ Test failed with error: {e}')
        import traceback
        traceback.print_exc()
        return False


# Run the test
if __name__ == "__main__":
    success = asyncio.run(test_real_providers())
    raise SystemExit(0 if success else 1)