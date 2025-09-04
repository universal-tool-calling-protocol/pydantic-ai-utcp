#!/usr/bin/env python3
"""Test script for PydanticAI UTCP adapters with real providers.

This script validates that real UTCP providers load and wrap into PydanticAITool
instances correctly, and that search works.
"""

import asyncio
from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig
from utcp.shared.provider import HttpProvider
from utcpPAI import (
    load_utcp_tools_for_pydantic_ai,
    search_utcp_tools_for_pydantic_ai,
    PydanticAITool,
)


async def test_real_providers_pydanticai() -> bool:
    """Test with real UTCP providers to validate PydanticAI wrapping functionality."""
    print("🧪 Testing PydanticAI UTCP Adapters with Real Providers")
    print("=" * 60)

    try:
        # Create UTCP client
        print("📡 Creating UTCP client...")
        config = UtcpClientConfig()
        client = await UtcpClient.create(config=config)
        print("✅ Client created successfully")

        # Register a real provider (OpenLibrary)
        print("\n📋 Registering OpenLibrary provider...")
        openlibrary_provider = HttpProvider(
            name="openlibrary",
            provider_type="http",
            http_method="GET",
            url="https://openlibrary.org/static/openapi.json",
            content_type="application/json",
        )
        await client.register_tool_provider(openlibrary_provider)
        print("✅ Provider registered successfully")

        # Load tools
        print("\n🔧 Loading tools...")
        tools = await load_utcp_tools_for_pydantic_ai(client)
        print(f"✅ Successfully loaded {len(tools)} PydanticAI tools")

        # Validate tools
        assert len(tools) > 0, "Should have loaded at least one tool"

        # Check tool properties
        for tool in tools[:3]:  # Check first 3 tools
            print(f"  📖 Tool: {tool.name}")
            print(f"     Description: {tool.description}")
            schema = tool.get_input_schema()
            print(f"     Input schema keys: {list(schema.get('properties', {}).keys())[:5]}")

            # Validate wrapper invariants
            assert isinstance(tool, PydanticAITool), "Tool should be a PydanticAITool"
            assert hasattr(tool, "input_model"), "PydanticAITool should expose input_model"

        # Test search functionality
        print("\n🔍 Testing search functionality (query='books')...")
        search_results = await search_utcp_tools_for_pydantic_ai(client, "books", max_results=3)
        print(f"✅ Search returned {len(search_results)} results")

        # Validate search results are reasonable
        for tool in search_results:
            print(f"  🔎 Found: {tool.name}")
            assert isinstance(tool, PydanticAITool)

        print("\n🎉 PydanticAI real-provider tests completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_real_providers_pydanticai())
    raise SystemExit(0 if success else 1)
