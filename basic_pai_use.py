"""Basic usage example for PydanticAI UTCP Adapters.

This example demonstrates how to:
1. Set up a UTCP client with providers
2. Load tools from UTCP providers
3. Convert them to PydanticAI-compatible tools
"""

import asyncio
from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig
from utcp.shared.provider import HttpProvider
from utcpPAI import load_utcp_tools_for_pydantic_ai, search_utcp_tools_for_pydantic_ai


async def main():
    """Main example function."""
    print("🚀 Basic PydanticAI UTCP Adapters Usage")
    print("=" * 40)
    
    # Create UTCP client directly (no temporary files needed)
    print("📡 Creating UTCP client...")
    config = UtcpClientConfig()
    client = await UtcpClient.create(config=config)
    
    # Register providers using Provider objects directly
    print("📡 Registering providers...")
    
    # Register Petstore API provider
    petstore_provider = HttpProvider(
        name="petstore",
        provider_type="http",
        url="https://petstore.swagger.io/v2/swagger.json",
        http_method="GET"
    )
    await client.register_tool_provider(petstore_provider)
    
    # Register OpenLibrary provider as additional example
    try:
        openlibrary_provider = HttpProvider(
            name="openlibrary",
            provider_type="http",
            http_method="GET",
            url="https://openlibrary.org/static/openapi.json",
            content_type="application/json"
        )
        await client.register_tool_provider(openlibrary_provider)
        print("✅ Successfully registered both providers")
    except Exception as e:
        print(f"Note: OpenLibrary provider registration failed: {e}")
        print("✅ Petstore provider registered successfully")
    
    # Get all available tools and convert to PydanticAI format
    print("\n🔧 Loading tools...")
    tools = await load_utcp_tools_for_pydantic_ai(client)
    print(f"Found {len(tools)} PydanticAI tools:")
    
    for tool in tools[:5]:  # Show first 5 tools
        print(f"  - {tool.name}: {tool.description}")
        print(f"    Input Model: {tool.input_model.__name__}")
    
    if len(tools) > 5:
        print(f"  ... and {len(tools) - 5} more tools")
    
    # Search for tools
    if tools:
        print("\n🔍 Searching for tools with 'pet'...")
        search_results = await search_utcp_tools_for_pydantic_ai(client, "pet", max_results=3)
        print(f"Found {len(search_results)} matching tools:")
        for tool in search_results:
            print(f"  - {tool.name}: {tool.description}")
    
    # Get provider information from UTCP client
    print("\n📊 Provider information:")
    providers = await client.tool_repository.get_providers()
    for provider in providers:
        print(f"  - {provider.name}: {provider.provider_type}")
        tools_for_provider = await client.tool_repository.get_tools_by_provider(provider.name)
        print(f"    Tools: {len(tools_for_provider) if tools_for_provider else 0}")
    
    # Show tool schemas
    if tools:
        print(f"\n🔧 Example tool schema for '{tools[0].name}':")
        print(f"  Description: {tools[0].description}")
        print(f"  Input Schema: {tools[0].get_input_schema()}")
        
        # Show how the tool would be called
        print(f"\n💡 Usage example:")
        print(f"    # To call this tool:")
        print(f"    # result = await PydanticAITool.{tools[0].name}(**arguments)")
        print(f"    # where arguments match the schema above")
    
    if not tools:
        print("\n⚠️  No tools were loaded. This might be because:")
        print("   - The OpenAPI endpoints are not accessible")
        print("   - The endpoints don't provide valid OpenAPI specifications")
        print("   - Network connectivity issues")
    
    print("\n✅ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())