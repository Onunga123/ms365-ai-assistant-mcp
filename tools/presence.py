from graph_client import graph_get, graph_post

def register_presence_tools(mcp):

    @mcp.tool()
    def get_user_presence(user_id: str):
        """Get the current presence status of a user in Teams. Returns availability and activity"""
        return graph_get(f"users/{user_id}/presence")

    @mcp.tool()
    def get_multiple_presence(user_ids: str):
        """Get presence status for multiple users at once. user_ids: comma separated list of user IDs"""
        id_list = [uid.strip() for uid in user_ids.split(",")]
        data = {"ids": id_list}
        return graph_post("communications/getPresencesByUserId", data)

    @mcp.tool()
    def list_available_users(user_ids: str):
        """Check which users from a list are currently available in Teams. user_ids: comma separated"""
        id_list = [uid.strip() for uid in user_ids.split(",")]
        data = {"ids": id_list}
        result = graph_post("communications/getPresencesByUserId", data)
        if "value" in result:
            available = [
                p for p in result["value"]
                if p.get("availability") == "Available"
            ]
            return {
                "available_users": available,
                "total_checked": len(id_list),
                "total_available": len(available)
            }
        return result