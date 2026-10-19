from graph_client import graph_get, graph_post_raw

def register_onenote_tools(mcp):

    @mcp.tool()
    def list_notebooks(user_id: str):
        """List all OneNote notebooks for a user"""
        return graph_get(f"users/{user_id}/onenote/notebooks")

    @mcp.tool()
    def get_notebook(user_id: str, notebook_id: str):
        """Get details of a specific OneNote notebook"""
        return graph_get(f"users/{user_id}/onenote/notebooks/{notebook_id}")

    @mcp.tool()
    def list_sections(user_id: str, notebook_id: str):
        """List all sections in a OneNote notebook"""
        return graph_get(f"users/{user_id}/onenote/notebooks/{notebook_id}/sections")

    @mcp.tool()
    def list_pages(user_id: str, section_id: str):
        """List all pages in a OneNote section"""
        return graph_get(f"users/{user_id}/onenote/sections/{section_id}/pages")

    @mcp.tool()
    def get_page_content(user_id: str, page_id: str):
        """Get the full content of a OneNote page"""
        return graph_get(f"users/{user_id}/onenote/pages/{page_id}/content")

    @mcp.tool()
    def create_page(user_id: str, section_id: str, title: str, content: str):
        """Create a new page in a OneNote section"""
        # OneNote page creation requires an application/xhtml+xml body (not JSON), so it
        # is routed through graph_post_raw, which preserves the payload encoding and
        # Content-Type while inheriting the shared timeout, bounded retry, and
        # sanitized-error behavior.
        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>{title}</title>
            </head>
            <body>
                <p>{content}</p>
            </body>
        </html>
        """
        return graph_post_raw(
            f"users/{user_id}/onenote/sections/{section_id}/pages",
            body=html_content.encode("utf-8"),
            content_type="application/xhtml+xml",
        )

    @mcp.tool()
    def search_pages(user_id: str, search_query: str):
        """Search for pages across all OneNote notebooks"""
        return graph_get(f"users/{user_id}/onenote/pages?$search={search_query}")