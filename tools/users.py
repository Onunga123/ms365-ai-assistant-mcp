from graph_client import graph_get, graph_get_all
def register_user_tools(mcp):

    @mcp.tool()
    def list_users():
        """List all users in the Microsoft 365 tenant"""
        return graph_get_all("users?$select=id,displayName,mail,jobTitle,department")

    @mcp.tool()
    def get_user(user_id: str):
        """Get details of a specific user by their ID or email address"""
        return graph_get(f"users/{user_id}?$select=id,displayName,mail,jobTitle,department,mobilePhone")

    @mcp.tool()
    def list_user_direct_reports(user_id: str):
        """List all direct reports for a specific user"""
        return graph_get(f"users/{user_id}/directReports")

    @mcp.tool()
    def get_user_manager(user_id: str):
        """Get the manager of a specific user"""
        return graph_get(f"users/{user_id}/manager")