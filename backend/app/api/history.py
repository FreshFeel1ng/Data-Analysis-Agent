"""Audit history and query history API."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.core.auth import get_current_user
from app.api import api_router

router = APIRouter(prefix="/history", tags=["历史记录"])


@router.get("/queries")
async def query_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get user's query history."""
    query = select(AuditLog).where(
        AuditLog.user_id == user.id,
        AuditLog.action == "query",
    ).order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "detail": r.detail,
            "params": r.params,
            "success": r.success,
            "error_msg": r.error_msg,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


@router.get("/audit")
async def audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str = Query(None),
    user_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get audit logs (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可查看审计日志")

    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "username": r.username,
            "action": r.action,
            "tool_name": r.tool_name,
            "resource": r.resource,
            "detail": r.detail,
            "params": r.params,
            "ip_address": r.ip_address,
            "success": r.success,
            "error_msg": r.error_msg,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


api_router.include_router(router)
