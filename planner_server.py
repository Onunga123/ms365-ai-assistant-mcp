import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from tools.planner import register_planner_tools
from tools.email import register_email_tools
from tools.calendar import register_calendar_tools
from tools.users import register_user_tools
from tools.teams import register_teams_tools
from tools.onedrive import register_onedrive_tools
from tools.sharepoint import register_sharepoint_tools
from tools.contacts import register_contacts_tools
from tools.todo import register_todo_tools

mcp = FastMCP("Pharo AI Chief of Staff")

register_planner_tools(mcp)
register_email_tools(mcp)
register_calendar_tools(mcp)
register_user_tools(mcp)
register_teams_tools(mcp)
register_onedrive_tools(mcp)
register_sharepoint_tools(mcp)
register_contacts_tools(mcp)
register_todo_tools(mcp)

if __name__ == "__main__":
    mcp.run()