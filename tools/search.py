from graph_client import graph_post

def register_search_tools(mcp):

    @mcp.tool()
    def search_all_content(query: str, content_types: str = "message,driveItem,listItem,site"):
        """Search across all Microsoft 365 content including emails, files, SharePoint and Teams messages. content_types can be: message, driveItem, listItem, site, event"""
        data = {
            "requests": [
                {
                    "entityTypes": content_types.split(","),
                    "query": {
                        "queryString": query
                    },
                    "from": 0,
                    "size": 10
                }
            ]
        }
        return graph_post("search/query", data)

    @mcp.tool()
    def search_emails_content(query: str):
        """Search specifically through emails across the tenant"""
        data = {
            "requests": [
                {
                    "entityTypes": ["message"],
                    "query": {
                        "queryString": query
                    },
                    "from": 0,
                    "size": 10
                }
            ]
        }
        return graph_post("search/query", data)

    @mcp.tool()
    def search_files(query: str):
        """Search specifically through files in OneDrive and SharePoint"""
        data = {
            "requests": [
                {
                    "entityTypes": ["driveItem"],
                    "query": {
                        "queryString": query
                    },
                    "from": 0,
                    "size": 10
                }
            ]
        }
        return graph_post("search/query", data)

    @mcp.tool()
    def search_people(query: str):
        """Search for people across the organisation by name or role"""
        data = {
            "requests": [
                {
                    "entityTypes": ["person"],
                    "query": {
                        "queryString": query
                    },
                    "from": 0,
                    "size": 10
                }
            ]
        }
        return graph_post("search/query", data)