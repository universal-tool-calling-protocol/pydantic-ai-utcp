"""Authentication example for PydanticAI UTCP Adapters.

This example demonstrates how to configure different authentication methods
for UTCP providers when using PydanticAI with real APIs that require authentication.

Note: This is a demonstration of authentication patterns. The examples use
working test endpoints where possible, but real API usage would require
valid credentials.
"""

import asyncio
from typing import List, Optional

from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig
from utcp_http.http_call_template import HttpCallTemplate
from utcp.data.auth_implementations.api_key_auth import ApiKeyAuth
from utcp.data.auth_implementations.basic_auth import BasicAuth
from utcp.data.auth_implementations.oauth2_auth import OAuth2Auth
from pydantic_utcp_adapters import (
    load_utcp_tools_for_pydantic_ai,
    convert_utcp_tool_to_pydantic_ai
)


async def create_client_with_auth() -> UtcpClient:
    """Create and configure a UTCP client with authentication."""
    config = UtcpClientConfig()
    return await UtcpClient.create(config=config)


async def demonstrate_api_key_auth():
    """Demonstrate API key authentication with a working test endpoint."""
    print("🔑 API Key Authentication Example")
    print("-" * 40)
    
    client = await create_client_with_auth()
    
    # Example: API key in header (most common)
    api_key_provider = HttpCallTemplate(
        name="httpbin_headers",
        call_template_type="http",
        url="http://httpbin.org/headers",
        http_method="GET",
        auth=ApiKeyAuth(
            api_key="demo-api-key-12345",
            var_name="X-API-Key",
            location="header"
        )
    )
    
    try:
        await client.register_call_template(api_key_provider)
        tools = await load_utcp_tools_for_pydantic_ai(client)
        
        if tools:
            print(f"✅ Successfully registered provider with API key auth")
            print(f"   Found {len(tools)} tools")
            for tool in tools[:3]:  # Show first few tools to avoid too much output
                print(f"   - {tool.name}")
            if len(tools) > 3:
                print(f"   ... and {len(tools) - 3} more tools")
        else:
            print("⚠️  Provider registered but no tools found")
            
    except Exception as e:
        print(f"❌ API key auth failed: {e}")
    
    print()


async def demonstrate_basic_auth():
    """Demonstrate basic authentication with HTTPBin test endpoint."""
    print("🔐 Basic Authentication Example")
    print("-" * 40)
    
    client = await create_client_with_auth()
    
    # HTTPBin provides a working basic auth test endpoint
    basic_auth_provider = HttpCallTemplate(
        name="httpbin_basic_auth",
        call_template_type="http",
        url="http://httpbin.org/basic-auth/testuser/testpass",
        http_method="GET",
        auth=BasicAuth(
            username="testuser",
            password="testpass"
        )
    )
    
    try:
        await client.register_call_template(basic_auth_provider)
        tools = await load_utcp_tools_for_pydantic_ai(client)
        
        if tools:
            print(f"✅ Successfully registered provider with basic auth")
            print(f"   Found {len(tools)} tools")
            for tool in tools[:3]:
                print(f"   - {tool.name}")
            if len(tools) > 3:
                print(f"   ... and {len(tools) - 3} more tools")
        else:
            print("⚠️  Provider registered but no tools found")
            
    except Exception as e:
        print(f"❌ Basic auth failed: {e}")
    
    print()


async def demonstrate_oauth2_auth():
    """Demonstrate OAuth2 authentication configuration."""
    print("🌐 OAuth2 Authentication Example")
    print("-" * 40)
    
    client = await create_client_with_auth()
    
    # OAuth2 example (this would require real OAuth2 endpoints)
    oauth2_provider = HttpCallTemplate(
        name="oauth2_demo",
        call_template_type="http",
        url="https://api.github.com",  # GitHub API as example
        http_method="GET",
        auth=OAuth2Auth(
            token_url="https://github.com/login/oauth/access_token",
            client_id="your_github_client_id",
            client_secret="your_github_client_secret",
            scope="repo read:user"
        )
    )
    
    try:
        # This will fail without real credentials, but shows the pattern
        await client.register_call_template(oauth2_provider)
        tools = await load_utcp_tools_for_pydantic_ai(client)
        
        if tools:
            print(f"✅ Successfully registered provider with OAuth2")
            print(f"   Tools found: {len(tools)}")
        else:
            print("⚠️  Provider registered but no tools found")
            
    except Exception as e:
        print(f"❌ OAuth2 auth failed (expected without real credentials): {e}")
        print("   This demonstrates the OAuth2 configuration pattern")
    
    print()


async def demonstrate_environment_variables():
    """Show how to use environment variables for credentials."""
    print("🌍 Environment Variables for Authentication")
    print("-" * 40)
    
    client = await create_client_with_auth()
    
    # Example of using environment variables in provider config
    env_provider = HttpCallTemplate(
        name="env_auth_demo",
        call_template_type="http",
        url="http://httpbin.org/headers",
        http_method="GET",
        auth=ApiKeyAuth(
            api_key="${API_KEY}",  # Would be replaced with env var value
            var_name="Authorization",
            location="header"
        )
    )
    
    print("🔧 Example of using environment variables in auth config:")
    print("   auth=ApiKeyAuth(api_key=\"${API_KEY}\", ...)")
    print("\n   In your environment, set:")
    print("   export API_KEY=your_real_api_key")
    print("\n   Or create a .env file with:")
    print("   API_KEY=your_real_api_key")
    print("\n✅ Provider configured to use environment variables")
    print()


async def main():
    """Run all authentication examples."""
    print("🔐 PydanticAI UTCP Adapters - Authentication Examples")
    print("=" * 60)
    print("This example shows how to configure authentication for UTCP providers")
    print("when using PydanticAI. These patterns work with real APIs that")
    print("require authentication.\n")
    
    await demonstrate_api_key_auth()
    await demonstrate_basic_auth()
    await demonstrate_oauth2_auth()
    await demonstrate_environment_variables()
    
    print("📚 Summary of Authentication Methods:")
    print("   • API Key: Most common, key in header or query parameter")
    print("   • Basic Auth: Username/password, base64 encoded")
    print("   • OAuth2: Token-based, requires client credentials")
    print("   • Environment Variables: Secure credential storage")
    print()
    print("💡 Best Practices:")
    print("   • Never hardcode credentials in source code")
    print("   • Use environment variables for sensitive data")
    print("   • Rotate API keys regularly")
    print("   • Use least-privilege access scopes")
    print()
    print("✅ Authentication examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
