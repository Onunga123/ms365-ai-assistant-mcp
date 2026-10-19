from graph_client import graph_get, graph_post, graph_patch, graph_get_all, graph_get_etag

def register_planner_tools(mcp):

    @mcp.tool()
    def get_groups():
        """Get all Microsoft 365 groups in the tenant"""
        return graph_get_all("groups")

    @mcp.tool()
    def get_plans(group_id: str):
        """Get all Planner plans for a specific Microsoft 365 group"""
        return graph_get(f"groups/{group_id}/planner/plans")

    @mcp.tool()
    def get_buckets(plan_id: str):
        """Get all buckets in a Planner plan"""
        return graph_get_all(f"planner/plans/{plan_id}/buckets")
    @mcp.tool()
    def get_tasks(plan_id: str):
        """Get all tasks in a Planner plan"""
        return graph_get_all(f"planner/plans/{plan_id}/tasks")

    @mcp.tool()
    def create_task(plan_id: str, bucket_id: str, title: str):
        """Create a new task in a Planner plan"""
        data = {
            "planId": plan_id,
            "bucketId": bucket_id,
            "title": title
        }
        return graph_post("planner/tasks", data)

    @mcp.tool()
    def update_task(task_id: str, title: str = None, percent_complete: int = None):
        """Update an existing Planner task. percent_complete: 0=not started, 50=in progress, 100=complete"""
        # Fetch the current ETag through the shared client so the request inherits the
        # finite timeout, bounded retry, and sanitized-error behavior. The ETag is then
        # passed to graph_patch as the If-Match value to preserve optimistic concurrency.
        etag = graph_get_etag(f"planner/tasks/{task_id}")
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if percent_complete is not None:
            update_data["percentComplete"] = percent_complete
        return graph_patch(f"planner/tasks/{task_id}", update_data, etag)