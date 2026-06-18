from graph_client import graph_get, graph_post, graph_get_all

def register_teams_tools(mcp):

    @mcp.tool()
    def list_teams():
        """List all Microsoft Teams in the tenant"""
        return graph_get_all("groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')&$select=id,displayName,description")

    @mcp.tool()
    def list_channels(team_id: str):
        """List all channels in a specific Microsoft Team"""
        return graph_get_all(f"teams/{team_id}/channels")

    @mcp.tool()
    def get_channel(team_id: str, channel_id: str):
        """Get details of a specific Teams channel"""
        return graph_get(f"teams/{team_id}/channels/{channel_id}")

    @mcp.tool()
    def list_channel_messages(team_id: str, channel_id: str, top: int = 50):
        """List recent messages in a Teams channel"""
        return graph_get_all(f"teams/{team_id}/channels/{channel_id}/messages?$top={top}", max_items=top)

    @mcp.tool()
    def send_channel_message(team_id: str, channel_id: str, message: str):
        """Send a message to a Teams channel"""
        data = {
            "body": {
                "contentType": "text",
                "content": message
            }
        }
        return graph_post(f"teams/{team_id}/channels/{channel_id}/messages", data)

    @mcp.tool()
    def list_team_members(team_id: str):
        """List all members of a Microsoft Team"""
        return graph_get_all(f"teams/{team_id}/members")