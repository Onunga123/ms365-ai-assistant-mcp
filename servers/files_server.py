import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import verify_server_key
verify_server_key()

from mcp.server.fastmcp import FastMCP
from tools.onedrive import register_onedrive_tools
from tools.sharepoint import register_sharepoint_tools
from tools.todo import register_todo_tools
from tools.onenote import register_onenote_tools
from tools.excel import register_excel_tools
from tools.search import register_search_tools

mcp = FastMCP("M365 Files")

register_onedrive_tools(mcp)
register_sharepoint_tools(mcp)
register_todo_tools(mcp)
register_onenote_tools(mcp)
register_excel_tools(mcp)
register_search_tools(mcp)

if __name__ == "__main__":
    mcp.run()