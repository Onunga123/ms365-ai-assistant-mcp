from graph_client import graph_get, graph_post, graph_get_all

def register_sharepoint_tools(mcp):

    @mcp.tool()
    def list_sharepoint_sites():
        """List all SharePoint sites in the tenant"""
        return graph_get_all("sites?search=*")

    @mcp.tool()
    def get_sharepoint_site(site_id: str):
        """Get details of a specific SharePoint site"""
        return graph_get(f"sites/{site_id}")

    @mcp.tool()
    def list_site_lists(site_id: str):
        """List all lists in a SharePoint site"""
        return graph_get_all(f"sites/{site_id}/lists")

    @mcp.tool()
    def list_site_list_items(site_id: str, list_id: str):
        """List all items in a SharePoint list"""
        return graph_get_all(f"sites/{site_id}/lists/{list_id}/items?$expand=fields")

    @mcp.tool()
    def create_list_item(site_id: str, list_id: str, fields: dict):
        """Create a new item in a SharePoint list"""
        data = {"fields": fields}
        return graph_post(f"sites/{site_id}/lists/{list_id}/items", data)

    @mcp.tool()
    def list_site_drives(site_id: str):
        """List all document libraries in a SharePoint site"""
        return graph_get_all(f"sites/{site_id}/drives")

    @mcp.tool()
    def list_site_drive_items(site_id: str, drive_id: str):
        """List files in a SharePoint document library"""
        return graph_get_all(f"sites/{site_id}/drives/{drive_id}/root/children")