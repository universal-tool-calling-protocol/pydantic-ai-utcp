"""OpenAPI integration example for PydanticAI UTCP Adapters.

This example demonstrates how UTCP can automatically convert OpenAPI specifications
into UTCP tools that can be used with PydanticAI.
"""

import asyncio
import json
from pathlib import Path

from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig
from utcp_http.http_call_template import HttpCallTemplate
from pydantic_utcp_adapters import load_utcp_tools_for_pydantic_ai, search_utcp_tools_for_pydantic_ai


async def main():
    """Main example function demonstrating OpenAPI integration with PydanticAI."""
    
    print("PydanticAI OpenAPI Integration Example")
    print("=" * 50)
    print("This example shows how UTCP can automatically convert")
    print("OpenAPI specifications into usable tools with PydanticAI.")
    print()
    
    # Create UTCP client
    print("📡 Creating UTCP client...")
    config = UtcpClientConfig()
    client = await UtcpClient.create(config=config)
    
    # Example 1: Register OpenAPI specs directly
    print("📡 Registering OpenAPI providers...")
    
    openapi_endpoints = [
        {
            "name": "petstore",
            "url": "https://petstore.swagger.io/v2/swagger.json",
            "description": "Swagger Petstore - Classic OpenAPI example"
        },
        {
            "name": "httpbin", 
            "url": "https://httpbin.org/spec.json",
            "description": "HTTPBin - HTTP testing service"
        }
    ]
    
    registered_providers = []
    for endpoint in openapi_endpoints:
        try:
            print(f"  Registering {endpoint['name']}...")
            template = HttpCallTemplate(
                name=endpoint["name"],
                call_template_type="http",
                url=endpoint["url"],
                http_method="GET"
            )
            await client.register_manual(template)
            registered_providers.append(endpoint["name"])
            print(f"    ✅ Registered {endpoint['name']}")
        except Exception as e:
            print(f"    ❌ Failed to register {endpoint['name']}: {e}")
    
    # Example 2: Create and load from JSON config
    print("\n📄 Creating and loading from JSON config...")
    config_data = [
        {
            "name": "jsonplaceholder",
            "call_template_type": "http",
            "url": "https://jsonplaceholder.typicode.com",
            "http_method": "GET"
        }
    ]
    
    config_file = Path("pydantic_openapi_config.json")
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)
    
    # Load additional configurations
    try:
        with open(config_file) as f:
            for item in json.load(f):
                try:
                    template = HttpCallTemplate(**item)
                    await client.register_manual(template)
                    registered_providers.append(item["name"])
                    print(f"✅ Loaded {item['name']} from config")
                except Exception as e:
                    print(f"❌ Failed to load {item.get('name', 'unknown')}: {e}")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
    
    # Load all tools and convert to PydanticAI format
    print("\n🔧 Loading all tools...")
    tools = await load_utcp_tools_for_pydantic_ai(client)
    print(f"Found {len(tools)} PydanticAI tools from OpenAPI specs:")
    
    # Group tools by provider
    tools_by_provider = {}
    for tool in tools:
        provider = tool.name.split('.')[0] if '.' in tool.name else 'unknown'
        if provider not in tools_by_provider:
            tools_by_provider[provider] = []
        tools_by_provider[provider].append(tool)
    
    for provider, provider_tools in tools_by_provider.items():
        print(f"\n  📦 {provider} ({len(provider_tools)} tools):")
        for tool in provider_tools[:3]:  # Show first 3 tools
            print(f"    - {tool.name}")
        if len(provider_tools) > 3:
            print(f"    ... and {len(provider_tools) - 3} more tools")
    
    # Search for specific functionality
    print("\n🔍 Searching for specific functionality...")
    search_queries = ["user", "post", "get", "pet"]
    
    for query in search_queries:
        results = await search_utcp_tools_for_pydantic_ai(client, query, max_results=3)
        if results:
            print(f"\n  Query '{query}' found {len(results)} tools:")
            for tool in results:
                print(f"    - {tool.name}")
    
    # Show detailed schema for one tool
    if tools:
        example_tool = tools[0]
        print(f"\n📋 Example tool info for '{example_tool.name}':")
        print(f"  Description: {example_tool.description}")
        
        # Try to get the schema if available
        try:
            schema = example_tool.get_input_schema()
            print(f"  Input schema: {schema.schema()}")
        except Exception as e:
            print(f"  Could not get input schema: {e}")
    
    # Cleanup
    if config_file.exists():
        config_file.unlink()
    
    print("\n✅ PydanticAI OpenAPI integration example completed!")
    print(f"Successfully integrated {len(tools)} tools from OpenAPI specifications")


if __name__ == "__main__":
    asyncio.run(main())
