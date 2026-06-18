from graph_client import graph_get, graph_post, graph_patch, graph_delete

def register_todo_tools(mcp):

    @mcp.tool()
    def list_todo_lists(user_id: str):
        """List all Microsoft To Do task lists for a user"""
        return graph_get(f"users/{user_id}/todo/lists")

    @mcp.tool()
    def get_todo_list(user_id: str, list_id: str):
        """Get details of a specific To Do list"""
        return graph_get(f"users/{user_id}/todo/lists/{list_id}")

    @mcp.tool()
    def create_todo_list(user_id: str, display_name: str):
        """Create a new Microsoft To Do task list"""
        data = {"displayName": display_name}
        return graph_post(f"users/{user_id}/todo/lists", data)

    @mcp.tool()
    def list_todo_tasks(user_id: str, list_id: str):
        """List all tasks in a specific To Do list"""
        return graph_get(f"users/{user_id}/todo/lists/{list_id}/tasks")

    @mcp.tool()
    def create_todo_task(user_id: str, list_id: str, title: str, due_date: str = None):
        """Create a new task in a To Do list. due_date format: '2026-06-12'"""
        data = {"title": title}
        if due_date:
            data["dueDateTime"] = {
                "dateTime": f"{due_date}T00:00:00",
                "timeZone": "Africa/Nairobi"
            }
        return graph_post(f"users/{user_id}/todo/lists/{list_id}/tasks", data)

    @mcp.tool()
    def update_todo_task(user_id: str, list_id: str, task_id: str, title: str = None, status: str = None):
        """Update a To Do task. status options: notStarted, inProgress, completed"""
        data = {}
        if title:
            data["title"] = title
        if status:
            data["status"] = status
        return graph_patch(f"users/{user_id}/todo/lists/{list_id}/tasks/{task_id}", data)

    @mcp.tool()
    def delete_todo_task(user_id: str, list_id: str, task_id: str):
        """Delete a task from a To Do list"""
        return graph_delete(f"users/{user_id}/todo/lists/{list_id}/tasks/{task_id}")