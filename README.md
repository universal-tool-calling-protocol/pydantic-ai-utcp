# pydantic-utcp-adapters

Adapters that bridge UTCP (Unified Tool Calling Protocol) tools into PydanticAI. This lets you discover tools (e.g., from OpenAPI specs or manual configs) via UTCP and use them as PydanticAI tools with minimal glue code.

UTCP is a newly launched, modern alternative to MCP, aimed at standardized tool discovery, configuration, and invocation across protocols like HTTP, SSE, and text-based definitions.

![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue?logo=github)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![PDM](https://img.shields.io/badge/Build-PDM-1f6feb?logo=dependabot)

## Features

- Convert UTCP tools (from OpenAPI, HTTP endpoints, or text manuals) into PydanticAI tools.
- Simple discovery and search across providers.
- Async-first; integrates seamlessly with async workflows.
- Batteries-included examples: OpenAPI integration, direct usage, auth patterns, and real providers.

## Badges

- The CI badge above is a generic indicator. Once you push the included `ci.yml` workflow and know your GitHub org/repo, replace it with:
  `https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg`.

## Requirements

- Python 3.11+
- [PDM](https://pdm.fming.dev/) (Python package/dependency manager)
- Internet access for examples that fetch OpenAPI specs or hit public APIs

Key packages used by this project:
- utcp, utcp-http, utcp-text
- pydantic >= 2.x
- aiohttp
- pytest and pytest-asyncio for tests

## Compatibility

- Pydantic: v2.x (tested with 2.11.x)
- UTCP core: >= 1.0.4
- UTCP HTTP: >= 1.0.4
- UTCP Text: >= 1.0.2

## Project Layout

- `pydantic_utcp_adapters/` – Package source (exports the adapter types and utilities)
- `examples/` – Example scripts demonstrating real-world usage
- `tests/` – Test suite (pytest)

## Installation (Development)

We recommend using PDM for all tasks. From the project root (`utcp-pydantic/`):

1. Install dependencies and your project package into the PDM-managed virtual environment:
   ```bash
   pdm install
   ```

2. Verify the package can be imported:
   ```bash
   pdm run python -c "import pydantic_utcp_adapters; print('OK')"
   ```

If you add new runtime dependencies during development:
- Add via PDM (example: utcp-text):
  ```bash
  pdm add utcp_text
  ```
- Re-export a pinned `requirements.txt` for non-PDM environments:
  ```bash
  pdm export -f requirements -o requirements.txt
  ```

Note: With PDM, you typically do not edit `pyproject.toml` by hand for dependencies; use `pdm add`/`pdm remove`.

## Running Tests

From the project root:
- Run the complete test suite:
  ```bash
  pdm run pytest
  ```

- Run a single test file:
  ```bash
  pdm run pytest tests/test_pydantic_tools.py
  pdm run pytest tests/test_pydantic_real_providers.py
  ```

## Examples

All examples are async and may perform network operations. Ensure you have internet access.

- Basic usage:
  ```bash
  pdm run python examples/pydantic_basic_use.py
  ```

- Direct usage (register templates inline, load tools, perform a simple query):
  ```bash
  pdm run python examples/pydantic_direct_use.py
  ```
  Note: UTCP enforces secure URLs (HTTPS or localhost). If you use http://httpbin.org in your own experiments, switch to https://httpbin.org or localhost.

- OpenAPI integration (discover tools from OpenAPI specs like Swagger Petstore):
  ```bash
  pdm run python examples/pydantic_openapi.py
  ```

- Real providers (OpenLibrary + optional NewsAPI via manual text template):
  ```bash
  pdm run python examples/pydantic_providers.py
  ```
  This example tries to load `examples/newsapi_manual.json` if present. It requires `utcp-text`, which you can add with:
  ```bash
  pdm add utcp_text
  ```
  Path handling is script-relative, so running from the project root works out of the box.
  UTCP manual schema note: the current UTCP text manual format expects each tool to define a `tool_call_template` with a `call_template_type` field (for HTTP, SSE, etc.). For example:
  ```json
  {
    "name": "everything_get",
    "inputs": { "type": "object", "properties": { "q": { "type": "string" } }, "required": ["q"] },
    "tool_call_template": {
      "call_template_type": "http",
      "url": "https://newsapi.org/v2/everything",
      "http_method": "GET",
      "content_type": "application/json",
      "auth": {
        "auth_type": "api_key",
        "api_key": "$NEWS_API_KEY",
        "var_name": "X-Api-Key",
        "location": "header"
      }
    }
  }
  ```
  Avoid the older `tool_provider`/`provider_type` keys; they will fail validation in newer UTCP versions.

- Authentication patterns (API key, Basic, OAuth2):
  ```bash
  pdm run python examples/pydantic_auth.py
  ```
  The OAuth2 part contains placeholders and will log a controlled failure without real credentials. The script demonstrates patterns only.

### Environment Variables

Some providers (e.g., NewsAPI) need an API key. If you use `examples/newsapi_manual.json`, set:
```bash
export NEWS_API_KEY=your_real_key
```
You can also use a `.env` file if you prefer environment-based configuration.

## Quickstart (Code)

Minimal usage pattern:
```python
import asyncio
from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig
from utcp_http.http_call_template import HttpCallTemplate
from pydantic_utcp_adapters import load_utcp_tools_for_pydantic_ai, search_utcp_tools_for_pydantic_ai

async def main():
    config = UtcpClientConfig(
        manual_call_templates=[
            HttpCallTemplate(
                name="openlibrary",
                call_template_type="http",
                url="https://openlibrary.org/static/openapi.json",
                http_method="GET",
                content_type="application/json",
            ),
        ]
    )
    client = await UtcpClient.create(config=config)

    tools = await load_utcp_tools_for_pydantic_ai(client)
    print(f"Loaded {len(tools)} tools")

    results = await search_utcp_tools_for_pydantic_ai(client, "book", max_results=3)
    for tool in results:
        print(f"- {tool.name}: {tool.description}")

asyncio.run(main())
```

## Contributing

Contributions are welcome! To get started:
- Fork and clone the repo
- Create a feature branch
- Run tests locally with `pdm run pytest`
- Add or update examples as needed
- Submit a pull request with a clear description and any relevant context

Before submitting PRs, ensure:
- Code is formatted and typed reasonably
- Tests pass
- New features include example usage or tests where appropriate

## Troubleshooting

- ModuleNotFoundError for `pydantic_utcp_adapters`:
  - Ensure you ran `pdm install` in the project root and are using `pdm run` to execute commands.

- HTTP provider registration errors:
  - UTCP HTTP providers require secure URLs (HTTPS) or localhost. Switch non-secure URLs to `https://...` or use a localhost endpoint.

- Exporting requirements with hashes:
  - Depending on your PDM version, `--hashes` might be unsupported. Use:
    ```bash
    pdm export -f requirements -o requirements.txt
    ```

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Acknowledgements

- UTCP ecosystem: `utcp`, `utcp-http`, `utcp-text`
- PydanticAI
- PDM for dependency and environment management
