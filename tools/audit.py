from logger import read_logs

def register_audit_tools(mcp):

    @mcp.tool()
    def get_audit_logs(last_n: int = 50):
        """Get the last N audit log entries showing all actions taken through the MCP server"""
        return read_logs(last_n)

    @mcp.tool()
    def get_recent_actions(last_n: int = 10):
        """Get the most recent actions taken through the MCP server"""
        logs = read_logs(last_n)
        return {
            "total_shown": len(logs),
            "actions": logs
        }