#!/usr/bin/env python3
"""Real providers example for PydanticAI UTCP Adapters.

This example demonstrates the package working with actual UTCP call templates:
- OpenLibrary API (via OpenAPI specification)
- NewsAPI (via UTCP manual definition)

It shows how to load real tools, search them, and use them in practice with PydanticAI.
"""

import asyncio
import json
from pathlib import Path

from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig
from utcp_http.http_call_template import HttpCallTemplate
from utcp_text.text_call_template import TextCallTemplate
from pydantic_utcp_adapters import load_utcp_tools_for_pydantic_ai, search_utcp_tools_for_pydantic_ai


async def main():
    """Main example function demonstrating real UTCP call templates with PydanticAI."""
    print("=== PydanticAI UTCP Adapters - Real Call Templates Example ===")
    print("=" * 70)
    
    # Create UTCP client with call templates
    print("[CREATE] Creating UTCP client...")
    
    # Check if NewsAPI manual exists (resolve relative to this script directory)
    newsapi_file = Path(__file__).parent / "newsapi_manual.json"
    call_templates = [
        HttpCallTemplate(
            name="openlibrary",
            call_template_type="http",
            http_method="GET",
            url="https://openlibrary.org/static/openapi.json",
            content_type="application/json"
        )
    ]
    
    if newsapi_file.exists():
        call_templates.append(
            TextCallTemplate(
                name="newsapi",
                call_template_type="text",
                file_path=str(newsapi_file)
            )
        )
        print("  [FOUND] Found NewsAPI manual, including in configuration")
    else:
        print("  [WARNING] NewsAPI manual not found, using OpenLibrary only")
    
    config = UtcpClientConfig(manual_call_templates=call_templates)
    client = await UtcpClient.create(config=config)
    
    # Load all available tools
    print("\n[LOADING] Loading UTCP tools for PydanticAI...")
    try:
        tools = await load_utcp_tools_for_pydantic_ai(client)
        print(f"\n[INFO] Successfully loaded {len(tools)} tools")
        
        # Display available tools
        print("\n[TOOLS] Available tools:")
        for tool in tools[:5]:  # Show first 5 tools to avoid overwhelming output
            print(f"  [TOOL] {tool.name}")
        if len(tools) > 5:
            print(f"  ... and {len(tools) - 5} more tools")
    
    except Exception as e:
        print(f"[ERROR] Failed to load tools: {e}")
        return
    
    # Demonstrate tool search
    print("\n[SEARCH] Searching for specific tools...")
    search_queries = ["search", "book", "author", "news"]
    
    for query in search_queries:
        try:
            matching_tools = await search_utcp_tools_for_pydantic_ai(client, query, max_results=3)
            if matching_tools:
                print(f"\n  [QUERY] '{query}' -> {len(matching_tools)} matches:")
                for tool in matching_tools:
                    print(f"    [RESULT] {tool.name}")
            else:
                print(f"\n  [QUERY] '{query}' -> No matches")
        except Exception as e:
            print(f"  [ERROR] Search failed for '{query}': {e}")
    
    # Demonstrate tool execution (if tools are available)
    if tools:
        print(f"\n[TEST] Testing tool execution...")
        
        # Try to find a simple tool to test
        test_tool = None
        for tool in tools:
            if "search" in tool.name.lower() and "author" in tool.name.lower():
                test_tool = tool
                break
        
        if test_tool:
            try:
                print(f"\n  [TOOL] Testing tool: {test_tool.name}")
                print(f"  [TYPE] {type(test_tool).__name__}")
                
                # Print all non-private attributes for inspection
                print("\n  [ATTR] Tool attributes:")
                for attr in dir(test_tool):
                    if not attr.startswith('_'):
                        attr_value = getattr(test_tool, attr)
                        print(f"      {attr}: {type(attr_value).__name__}")
                
                # Try to get the function to call
                tool_func = None
                
                # Check for common method names that might be callable
                for method_name in ['__call__', 'func', '_run', 'run', 'invoke', 'call']:
                    if hasattr(test_tool, method_name) and callable(getattr(test_tool, method_name)):
                        tool_func = getattr(test_tool, method_name)
                        print(f"  [METHOD] Found callable method: {method_name}")
                        break
                
                if tool_func:
                    # Try to get input schema if available
                    input_schema = {}
                    if hasattr(test_tool, 'get_input_schema'):
                        try:
                            input_schema = test_tool.get_input_schema()
                            print(f"  [SCHEMA] Input schema: {input_schema}")
                        except Exception as e:
                            print(f"  [WARNING] Could not get input schema: {e}")
                    
                    # Try calling with different argument patterns
                    call_patterns = [
                        ({"q": "J.K. Rowling"}, "with query parameter"),
                        ({"query": "J.K. Rowling"}, "with query parameter (alternate name)"),
                        ({}, "with no arguments")
                    ]
                    
                    for args, desc in call_patterns:
                        try:
                            print(f"  [CALL] Attempting call {desc}: {args}")
                            if asyncio.iscoroutinefunction(tool_func):
                                result = await tool_func(**args)
                            else:
                                result = tool_func(**args)
                            
                            print(f"  [SUCCESS] Call successful!")
                            print(f"  [RESULT] Type: {type(result).__name__}")
                            
                            # Save result to file for inspection
                            import json
                            with open('tool_result.json', 'w', encoding='utf-8') as f:
                                if hasattr(result, 'model_dump'):
                                    json.dump(result.model_dump(), f, indent=2)
                                elif hasattr(result, 'dict'):
                                    json.dump(result.dict(), f, indent=2)
                                else:
                                    json.dump(str(result), f, indent=2)
                            
                            # Print result preview
                            result_str = str(result)
                            print(f"  [RESULT] Result preview: {result_str[:200]}...")
                            print(f"  [FILE] Full result saved to tool_result.json")
                            break  # Stop on first successful call
                            
                        except Exception as e:
                            print(f"  [ERROR] Call failed: {e}")
                            continue
                    
                else:
                    print("  [WARNING] No callable method found on the tool object")
                    
            except Exception as e:
                print(f"  [ERROR] Unexpected error: {e}")
                import traceback
                print(f"  Stack trace: {traceback.format_exc()}")
        else:
            print("  [WARNING] No suitable test tool found")
    
    print("\n[SUCCESS] PydanticAI example completed!")


if __name__ == "__main__":
    asyncio.run(main())
