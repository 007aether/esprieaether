"""
⚡ EsprieAether - MCP Client
عميل لاختبار MCP Server
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path.home() / "AETHER_V8"

logger = logging.getLogger("mcp_client")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class MCPClient:
    """عميل MCP"""

    def __init__(self):
        self.server_params = StdioServerParameters(
            command=str(BASE_DIR / ".venv" / "bin" / "python3"),
            args=[str(BASE_DIR / "src" / "mcp_server.py")],
            env=None,
        )

    async def list_tools(self) -> list:
        """اعرض الأدوات المتاحة"""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

    async def call_tool(self, name: str, args: dict = None) -> str:
        """استدعِ أداة"""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, args or {})
                # استخرج النص
                texts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        texts.append(content.text)
                return chr(10).join(texts)


async def main():
    """اختبار كامل"""
    print("═" * 60)
    print("🔌 MCP Client Test")
    print("═" * 60)

    client = MCPClient()

    # 1. اعرض الأدوات
    print()
    print("▶ الأدوات المتاحة:")
    try:
        tools = await client.list_tools()
        for t in tools:
            print("  ✅ " + t.name)
        print()
        print("  إجمالي: " + str(len(tools)) + " أداة")
    except Exception as e:
        print("  ❌ " + str(e)[:200])
        return

    # 2. اختبر أدوات
    print()
    print("▶ اختبار get_stats:")
    try:
        result = await client.call_tool("get_stats")
        print("  " + result.replace(chr(10), chr(10) + "  "))
    except Exception as e:
        print("  ❌ " + str(e)[:200])

    print()
    print("▶ اختبار get_vpn_status:")
    try:
        result = await client.call_tool("get_vpn_status")
        print("  " + result)
    except Exception as e:
        print("  ❌ " + str(e)[:200])

    print()
    print("▶ اختبار get_airdrops(3):")
    try:
        result = await client.call_tool("get_airdrops", {"limit": 3})
        print("  " + result.replace(chr(10), chr(10) + "  "))
    except Exception as e:
        print("  ❌ " + str(e)[:200])


if __name__ == "__main__":
    asyncio.run(main())
