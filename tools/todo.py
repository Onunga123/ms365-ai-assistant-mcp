import os
import zoneinfo  # Python 3.9+ standard library

from graph_client import graph_get, graph_post, graph_patch, graph_delete

_DEFAULT_TIMEZONE_FALLBACK = "Africa/Nairobi"


def _get_default_timezone() -> str:
    """Return the configured default IANA timezone for To Do task due dates.

    Reads DEFAULT_TIMEZONE from the environment, falling back to Africa/Nairobi
    when unset or empty. An explicitly configured value is validated against the
    IANA timezone database via zoneinfo; an invalid value raises a clear,
    non-sensitive error rather than silently substituting another timezone.
    """
    configured = os.getenv("DEFAULT_TIMEZONE")
    if not configured or not configured.strip():
        return _DEFAULT_TIMEZONE_FALLBACK
    tz_name = configured.strip()
    try:
        zoneinfo.ZoneInfo(tz_name)
    except Exception as exc:
        raise Exception(
            f"DEFAULT_TIMEZONE is set to an invalid IANA timezone '{tz_name}'. "
            f"Use a valid timezone name (for example 'Africa/Nairobi', 'UTC', "
            f"'Europe/London') or leave it unset to use the default."
        ) from exc
    return tz_name


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
            tz = _get_default_timezone()
            data["dueDateTime"] = {
                "dateTime": f"{due_date}T00:00:00",
                "timeZone": tz
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
