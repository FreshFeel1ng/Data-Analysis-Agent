"""Query history API — full details with delete support."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.user import User
from app.models.query_history import QueryHistory
from app.core.auth import get_current_user
from app.api import api_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["历史记录"])


@router.get("/queries")
async def query_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户的完整查询历史（含 SQL、结果、图表）。"""
    result = await db.execute(
        select(QueryHistory)
        .where(QueryHistory.user_id == user.id)
        .order_by(desc(QueryHistory.created_at))
        .offset(offset)
        .limit(limit)
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "question": r.question,
            "sql": r.sql,
            "result_json": r.result_json,
            "chart_data": r.chart_data,
            "explanation": r.explanation,
            "db_name": r.db_name,
            "success": r.success,
            "error_msg": r.error_msg,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


@router.delete("/queries/{record_id}")
async def delete_query(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除一条查询历史记录。"""
    result = await db.execute(
        select(QueryHistory).where(
            QueryHistory.id == record_id,
            QueryHistory.user_id == user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(record)
    await db.commit()
    return {"message": "删除成功"}


api_router.include_router(router)
