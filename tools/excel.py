from graph_client import graph_get, graph_post, graph_patch

def register_excel_tools(mcp):

    @mcp.tool()
    def list_excel_files(user_id: str):
        """List all Excel files in a user's OneDrive"""
        return graph_get(f"users/{user_id}/drive/root/search(q='.xlsx')?$select=id,name,webUrl,lastModifiedDateTime")

    @mcp.tool()
    def list_excel_worksheets(user_id: str, file_id: str):
        """List all worksheets in an Excel file"""
        return graph_get(f"users/{user_id}/drive/items/{file_id}/workbook/worksheets")

    @mcp.tool()
    def get_excel_range(user_id: str, file_id: str, sheet_name: str, range_address: str):
        """Get data from a specific range in an Excel worksheet. range_address example: 'A1:D10'"""
        return graph_get(f"users/{user_id}/drive/items/{file_id}/workbook/worksheets/{sheet_name}/range(address='{range_address}')")

    @mcp.tool()
    def update_excel_range(user_id: str, file_id: str, sheet_name: str, range_address: str, values: list):
        """Update values in a specific Excel range. values is a 2D array e.g. [['Name','Age'],['John',30]]"""
        data = {"values": values}
        return graph_patch(
            f"users/{user_id}/drive/items/{file_id}/workbook/worksheets/{sheet_name}/range(address='{range_address}')",
            data
        )

    @mcp.tool()
    def get_excel_table(user_id: str, file_id: str, table_name: str):
        """Get all rows from a named Excel table"""
        return graph_get(f"users/{user_id}/drive/items/{file_id}/workbook/tables/{table_name}/rows")

    @mcp.tool()
    def add_excel_row(user_id: str, file_id: str, table_name: str, values: list):
        """Add a new row to a named Excel table. values is a list e.g. ['John', 30, 'Nairobi']"""
        data = {"values": [values]}
        return graph_post(
            f"users/{user_id}/drive/items/{file_id}/workbook/tables/{table_name}/rows/add",
            data
        )

    @mcp.tool()
    def create_excel_chart(user_id: str, file_id: str, sheet_name: str, chart_type: str, data_range: str):
        """Create a chart in an Excel worksheet. chart_type options: ColumnClustered, Line, Pie, Bar"""
        data = {
            "type": chart_type,
            "sourceData": data_range,
            "seriesBy": "Auto"
        }
        return graph_post(
            f"users/{user_id}/drive/items/{file_id}/workbook/worksheets/{sheet_name}/charts/add",
            data
        )