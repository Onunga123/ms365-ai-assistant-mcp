import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import verify_server_key
verify_server_key()

from mcp.server.fastmcp import FastMCP
from tools.email import register_email_tools
from tools.calendar import register_calendar_tools
from tools.teams import register_teams_tools
from tools.contacts import register_contacts_tools
from tools.meetings import register_meetings_tools
from tools.drafts import register_drafts_tools
from tools.shared_mailbox import register_shared_mailbox_tools
from tools.presence import register_presence_tools

mcp = FastMCP("M365 Communication")

register_email_tools(mcp)
register_calendar_tools(mcp)
register_teams_tools(mcp)
register_contacts_tools(mcp)
register_meetings_tools(mcp)
register_drafts_tools(mcp)
register_shared_mailbox_tools(mcp)
register_presence_tools(mcp)

if __name__ == "__main__":
    mcp.run()