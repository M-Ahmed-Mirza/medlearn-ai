"""
MedLearn AI - MCP Server Launcher

Starts the MedLearn AI MCP server over stdio transport (the standard for
local MCP clients like Claude Desktop).

Run:
    python -m scripts.run_mcp_server

To connect from Claude Desktop, add this to your claude_desktop_config.json:

    {
      "mcpServers": {
        "medlearn-ai": {
          "command": "python",
          "args": ["-m", "scripts.run_mcp_server"],
          "cwd": "F:\\\\Hackathon\\\\Projects\\\\medlearn-ai"
        }
      }
    }

To explore/test with the MCP Inspector instead:
    npx @modelcontextprotocol/inspector python -m scripts.run_mcp_server
"""

from mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
