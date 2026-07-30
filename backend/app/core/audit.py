import logging
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    user_id: int,
    username: str,
    action: str,
    *,
    tool_name: Optional[str] = None,
    resource: Optional[str] = None,
    detail: Optional[str] = None,
    params: Optional[dict] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    error_msg: Optional[str] = None,
):
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        tool_name=tool_name,
        resource=resource,
        detail=detail,
        params=params,
        ip_address=ip_address,
        success=success,
        error_msg=error_msg,
    )
    db.add(entry)
    await db.commit()
    logger.info(f"AUDIT: user={username} action={action} tool={tool_name} success={success}")
