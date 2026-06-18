from graph_client import graph_get, graph_post, graph_delete, graph_get_all

def register_onedrive_tools(mcp):

    @mcp.tool()
    def list_drives(user_id: str):
        """List all OneDrive drives for a user"""
        return graph_get(f"users/{user_id}/drives")

    @mcp.tool()
    def list_drive_items(user_id: str, folder_path: str = "root"):
        """List files and folders in a user's OneDrive. folder_path defaults to root"""
        return graph_get_all(f"users/{user_id}/drive/{folder_path}/children")
    @mcp.tool()
    def get_drive_item(user_id: str, item_id: str):
        """Get details of a specific file or folder in OneDrive"""
        return graph_get(f"users/{user_id}/drive/items/{item_id}")

    @mcp.tool()
    def search_drive(user_id: str, search_query: str):
        """Search for files in a user's OneDrive"""
        return graph_get_all(f"users/{user_id}/drive/root/search(q='{search_query}')")

    @mcp.tool()
    def create_folder(user_id: str, folder_name: str, parent_id: str = "root"):
        """Create a new folder in OneDrive"""
        data = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        return graph_post(f"users/{user_id}/drive/items/{parent_id}/children", data)

    @mcp.tool()
    def delete_drive_item(user_id: str, item_id: str):
        """Delete a file or folder from OneDrive"""
        return graph_delete(f"users/{user_id}/drive/items/{item_id}")