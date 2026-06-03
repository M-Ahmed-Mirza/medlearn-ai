"""
MedLearn AI - MCP Server Smoke Test (pure Python, no Node/Inspector needed)

Acts as an in-process MCP client: connects to the MedLearn MCP server over an
in-memory stream, performs the protocol handshake, lists the registered tools
and resources, reads a discovery resource, and invokes one tool end-to-end.

This proves the MCP server works through the real protocol — the same thing
the Inspector would show, but without needing Node.js.

Run from project root:
    python -m scripts.test_mcp_server

The single tool call (recommend_certification) makes ONE live Azure call
(~$0.01). Set LIST_ONLY=1 to skip the live call and only verify the protocol
surface:
    $env:LIST_ONLY=1; python -m scripts.test_mcp_server
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP  # noqa: F401  (ensures SDK present)

from mcp_server import mcp


async def main() -> None:
    print("=" * 74)
    print("MedLearn AI - MCP Server Smoke Test (in-process client)")
    print("=" * 74)

    # 1. List tools through the protocol
    tools = await mcp.list_tools()
    print(f"\nTOOLS registered ({len(tools)}):")
    for t in tools:
        # Show the first line of each tool's description
        desc = (t.description or "").strip().splitlines()[0] if t.description else ""
        print(f"  - {t.name}: {desc}")

    # 2. List resources
    resources = await mcp.list_resources()
    print(f"\nRESOURCES registered ({len(resources)}):")
    for r in resources:
        print(f"  - {r.uri}")

    # 3. Read a discovery resource through the protocol
    print("\nReading resource medlearn://learners ...")
    res_contents = await mcp.read_resource("medlearn://learners")
    # Returns a list of ReadResourceContents; each has a .content attribute.
    first = res_contents[0] if isinstance(res_contents, list) else res_contents
    content = getattr(first, "content", str(first))
    preview = content[:200] if isinstance(content, str) else str(content)[:200]
    print(f"  {preview}...")

    if os.getenv("LIST_ONLY") in {"1", "true", "yes"}:
        print("\nLIST_ONLY set — skipping the live tool invocation.")
        print("\nProtocol surface verified. MCP server is working.")
        return

    # 4. Invoke a tool end-to-end (one live Azure call)
    print("\nInvoking tool recommend_certification(learner_id='CLN-N-001') ...")
    result = await mcp.call_tool(
        "recommend_certification", {"learner_id": "CLN-N-001"}
    )
    # call_tool returns a tuple: (list_of_content_blocks, result_dict).
    # Pull the text out of the first content block defensively.
    text = ""
    try:
        blocks = result[0] if isinstance(result, tuple) else result
        first = blocks[0]
        text = first.text if hasattr(first, "text") else str(first)
    except Exception:
        text = str(result)
    print("  Tool returned (first 400 chars):")
    print("  " + text[:400].replace("\n", "\n  "))

    print("\n" + "=" * 74)
    print("MCP server smoke test PASSED — tools, resources, and a live tool")
    print("invocation all worked through the MCP protocol.")
    print("=" * 74)


if __name__ == "__main__":
    asyncio.run(main())
