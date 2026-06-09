from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.getenv("MONGODB_MCP_URL", "http://127.0.0.1:3000/mcp")


def print_result(title: str, result: Any) -> None:
    print(f"\n=== {title} ===")

    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)

        if text is None:
            print(item)
            continue

        try:
            print(json.dumps(json.loads(text), indent=2))
        except json.JSONDecodeError:
            print(text)


async def main() -> None:
    async with streamablehttp_client(MCP_URL) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("Available MongoDB MCP tools:")
            for tool in tools.tools:
                print(f"- {tool.name}")

            await run_if_available(session, tools.tools, "list-databases", {})

            await run_if_available(
                session,
                tools.tools,
                "list-collections",
                {"database": "mim_incident_intelligence"},
            )

            await run_if_available(
                session,
                tools.tools,
                "count",
                {
                    "database": "mim_incident_intelligence",
                    "collection": "incidents",
                    "query": {},
                },
            )

            await run_if_available(
                session,
                tools.tools,
                "find",
                {
                    "database": "mim_incident_intelligence",
                    "collection": "incidents",
                    "filter": {"service": "Salesforce"},
                    "limit": 5,
                },
            )


async def run_if_available(
    session: ClientSession,
    tools: list[Any],
    tool_name: str,
    arguments: dict[str, Any],
) -> None:
    available = {tool.name: tool for tool in tools}

    if tool_name not in available:
        print(f"\nSkipping unavailable tool: {tool_name}")
        return

    try:
        result = await session.call_tool(tool_name, arguments=arguments)
    except Exception as exc:
        print(f"\n{tool_name} failed: {exc}")
        print("Tool input schema:")
        print(json.dumps(available[tool_name].inputSchema, indent=2))
        return

    print_result(tool_name, result)


if __name__ == "__main__":
    asyncio.run(main())
