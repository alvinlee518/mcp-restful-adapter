#!/usr/bin/env python3
"""Example: Build an agent that uses mcp-restful-adapter tools.

Shows how to programmatically connect to the MCP server and call tools
from Python — the building block for any AI agent.

Usage:
    uv run python examples/agent_usage.py
"""

import asyncio
import json
import os

from fastmcp import Client
from fastmcp.client.transports.stdio import StdioTransport


async def main():
    # ── 1. 连接 MCP Server ───────────────────────────────────────
    # 方式 A: 子进程模式（推荐，隔离性好）
    transport = StdioTransport(
        command="uv",
        args=["run", "mcp-restful-adapter"],
        env={
            **os.environ,
            "API_SPEC_URL": "https://petstore3.swagger.io/api/v3/openapi.json",
            "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
            "API_METHODS": "GET,POST,PUT,DELETE",
            "API_TAGS": "pet",
        },
    )
    client = Client(transport)

    # 方式 B: 内存模式（更快，适合开发调试）
    # from mcp_restful_adapter.server import build_server
    # from mcp_restful_adapter.spec_fetcher import fetch_spec
    # spec = await fetch_spec("https://petstore3.swagger.io/api/v3/openapi.json")
    # server = build_server(spec, base_url="https://petstore3.swagger.io/api/v3",
    #                       tags={"pet"}, methods={"GET", "POST", "PUT", "DELETE"})
    # client = Client(server)

    async with client:
        # ── 2. 获取可用 tools ────────────────────────────────────
        tools = await client.list_tools()
        print(f"可用 tools ({len(tools)}):")
        for tool in tools:
            params = list(tool.inputSchema.get("properties", {}).keys())
            print(f"  • {tool.name}({', '.join(params)})")

        # ── 3. 调用 tool ─────────────────────────────────────────
        # 查找宠物
        print("\n--- 查找可用宠物 ---")
        result = await client.call_tool(
            "findPetsByStatus",
            {"status": "available"},
            raise_on_error=False,
        )
        if not result.is_error and result.structured_content:
            pets = result.structured_content.get("result", [])
            print(f"找到 {len(pets)} 只宠物")
            for pet in pets[:3]:
                print(f"  #{pet['id']} {pet['name']} [{pet['status']}]")

            # ── 4. 用上一次的结果继续调用 ─────────────────────────
            if pets:
                pet_id = pets[0]["id"]
                print(f"\n--- 查询宠物 #{pet_id} 详情 ---")
                result = await client.call_tool(
                    "getPetById",
                    {"petId": pet_id},
                    raise_on_error=False,
                )
                if not result.is_error and result.structured_content:
                    pet = result.structured_content
                    print(f"  名字: {pet.get('name')}")
                    print(f"  状态: {pet.get('status')}")
                    if pet.get("category"):
                        print(f"  分类: {pet['category'].get('name')}")

        # ── 5. 创建新宠物 ────────────────────────────────────────
        print("\n--- 创建新宠物 ---")
        result = await client.call_tool(
            "addPet",
            {
                "name": "Claude",
                "status": "available",
                "photoUrls": ["https://example.com/cat.jpg"],
                "category": {"name": "AI Pets"},
            },
            raise_on_error=False,
        )
        if not result.is_error and result.structured_content:
            pet = result.structured_content
            print(f"  创建成功! ID: {pet.get('id')}")
            print(f"  名字: {pet.get('name')}")


if __name__ == "__main__":
    asyncio.run(main())
