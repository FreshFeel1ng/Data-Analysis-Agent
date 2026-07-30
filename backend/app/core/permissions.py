from typing import List, Optional, Set
from functools import wraps
from fastapi import HTTPException, status
from app.models.user import User

# Tool permissions: {tool_name: allowed_roles (empty means all)}
TOOL_PERMISSIONS: dict[str, Set[str]] = {
    "execute_sql": set(),  # all roles
    "get_schema": set(),
    "get_table_sample": set(),
    "generate_chart": set(),
    "add_training_data": {"admin"},  # only admin
    "manage_db_connection": {"admin"},
    "manage_users": {"admin"},
}


def check_tool_permission(user: User, tool_name: str) -> bool:
    """Check if a user has permission to use a tool."""
    allowed = TOOL_PERMISSIONS.get(tool_name)
    if allowed is None or len(allowed) == 0:
        return True  # no restriction
    return user.role in allowed


def require_role(*roles: str):
    """Dependency: require user to have one of the given roles."""
    async def role_checker(user: User):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {roles}"
            )
        return user
    return role_checker


def require_admin():
    return require_role("admin")


def get_user_accessible_tools(user: User) -> List[str]:
    """Return list of tool names accessible to this user."""
    return [
        name for name, allowed in TOOL_PERMISSIONS.items()
        if len(allowed) == 0 or user.role in allowed
    ]
