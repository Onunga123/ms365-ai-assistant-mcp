import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import verify_server_key
verify_server_key()

from mcp.server.fastmcp import FastMCP
from tools.planner import register_planner_tools
from tools.users import register_user_tools
from tools.audit import register_audit_tools
from tools.health import register_health_tools

mcp = FastMCP("M365 Core")

register_planner_tools(mcp)
register_user_tools(mcp)
register_audit_tools(mcp)
register_health_tools(mcp)

if __name__ == "__main__":
    mcp.run()