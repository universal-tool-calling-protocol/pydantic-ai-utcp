"""Simple direct usage example for PydanticAI UTCP Adapters.

This example demonstrates the simplified approach:
1. Create a UTCP client directly
2. Register call templates dynamically
3. Load and use tools with PydanticAI
"""

import asyncio
import asyncio
from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig
from utcp_http.http_call_template import HttpCallTemplate
from pydantic_utcp_adapters import load_utcp_tools_for_pydantic_ai, search_utcp_tools_for_pydantic_ai


async def main():
    """Main example function."""
    print("🚀 Simple Direct UTCP + PydanticAI Integration")
    print("=" * 50)
    
    # Create UTCP client with call templates
    print("📡 Creating UTCP client with call templates...")
    
    # Option 1: Using a dictionary for configuration
    config = {
        "tool_repository": {"tool_repository_type": "in_memory"},
        "tool_search_strategy": {"tool_search_strategy_type": "tag_and_description_word_match"},
        "manual_call_templates": [
            {
                "name": "openlibrary",
                "call_template_type": "http",
                "http_method": "GET",
                "url": "https://openlibrary.org/static/openapi.json",
                "content_type": "application/json"
            },
            {
                "name": "httpbin",
                "call_template_type": "http",
                "http_method": "POST",
                "url": "http://httpbin.org/anything",
                "content_type": "application/json"
            }
        ]
    }
    
    # Create the client with the configuration
    client = await UtcpClient.create(config=config)
    
    # Alternative: Using UtcpClientConfig object
    # config_obj = UtcpClientConfig(
    #     tool_repository={"tool_repository_type": "in_memory"},
    #     tool_search_strategy={"tool_search_strategy_type": "tag_and_description_word_match"},
    #     manual_call_templates=[
    #         HttpCallTemplate(
    #             name="openlibrary",
    #             call_template_type="http",
    #             http_method="GET",
    #             url="https://openlibrary.org/static/openapi.json",
    #             content_type="application/json"
    #         ),
    #         HttpCallTemplate(
    #             name="httpbin",
    #             call_template_type="http",
    #             http_method="POST",
    #             url="http://httpbin.org/anything",
    #             content_type="application/json"
    #         )
    #     ]
    # )
    # client = await UtcpClient.create(config=config_obj)
    
    print("✅ Call templates registered successfully")
    
    # Load all tools and convert to PydanticAI format
    print("\n🔧 Loading tools...")
    tools = await load_utcp_tools_for_pydantic_ai(client)
    print(f"Found {len(tools)} PydanticAI tools:")
    
    for tool in tools[:5]:  # Show first 5 tools
        metadata = tool.get_metadata()
        print(f"  - {tool.name}")
        
    # Example of calling a tool directly
    if tools:
        try:
            print("\n🔍 Example: Searching for books about Python...")
            # Find a search tool (adjust the condition based on available tools)
            search_tool = next((t for t in tools if 'search' in t.name.lower() and 'books' in t.name.lower()), None)
            
            if search_tool:
                print(f"Using tool: {search_tool.name}")
                result = await search_tool.invoke({"q": "Python programming"})
                print(f"Search result: {result}")
            else:
                print("No search tool found in the available tools.")
                print("Available tools:", [t.name for t in tools])
        except Exception as e:
            print(f"Error calling tool: {e}")
        print(f"    Description: {tool.description}")
        print(f"    Call Template: {metadata.get('call_template', 'unknown')}")
        print(f"    Type: {metadata.get('call_template_type', 'unknown')}")
    
    if len(tools) > 5:
        print(f"  ... and {len(tools) - 5} more tools")
    
    # Search for specific tools
    print("\n🔍 Searching for book-related tools...")
    book_tools = await search_utcp_tools_for_pydantic_ai(client, "book", max_results=3)
    print(f"Found {len(book_tools)} book-related tools:")
    
    for tool in book_tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # Use a tool if available
    if book_tools:
        print(f"\n🎯 Tool info: {book_tools[0].name}")
        try:
            print(f"Input schema: {book_tools[0].input_model.schema()}")
            print("\n💡 Usage example:")
            print(f"    # To call this tool:")
            print(f"    # result = await {book_tools[0].name}(**arguments)")
            print(f"    # where arguments match the schema above")
        except Exception as e:
            print(f"Tool test failed: {e}")
    
    print("\n✅ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
