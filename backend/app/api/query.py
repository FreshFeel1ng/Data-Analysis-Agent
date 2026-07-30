"""Text-to-SQL Query API."""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.db_connection import DBConnection
from app.schemas.query import QueryRequest, QueryResponse
from app.core.auth import get_current_user
from app.core.permissions import check_tool_permission
from app.core.audit import log_action
from app.services.db_service import db_service
from app.services.training_service import get_training_context, build_training_prompt
from app.services.milvus_service import milvus_service
from app.agent.tools import tool_registry
from app.api import api_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["查询"])


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Natural language to SQL query with AI analysis."""
    # Get DB connection
    result = await db.execute(select(DBConnection).where(DBConnection.id == req.db_connection_id))
    db_conn = result.scalar_one_or_none()
    if not db_conn or not db_conn.is_active:
        raise HTTPException(status_code=404, detail="数据库连接不存在或已禁用")

    # Get training context
    training_ctx = await get_training_context(db, req.db_connection_id)
    training_prompt = build_training_prompt(training_ctx)

    # Search similar examples from Milvus
    similar = await milvus_service.search_similar_examples(req.question)
    similar_text = (
        "\n".join(
            f"- Q: {ex['question']}\n  工具: {ex['tool_name']}, 参数: {ex['tool_params']}"
            for ex in similar
        )
    ) if similar else ""

    # Bind context to tool registry
    async with db_service.get_session(db_conn) as target_session:
        tool_registry.bind_context(
            db_session=target_session,
            app_db=db,
            db_conn=db_conn,
            user=user,
            milvus=milvus_service,
        )

        # Run agent
        from app.agent.graph import run_analysis
        result_data = await run_analysis(
            question=req.question,
            db_connection_id=req.db_connection_id,
            training_context=training_prompt,
            similar_examples=similar_text,
        )

    # Audit log
    await log_action(
        db,
        user.id,
        user.username,
        "query",
        detail=req.question,
        params={
            "db_connection_id": req.db_connection_id,
            "db_name": db_conn.name,
            "sql": result_data.get("sql"),
            "tools_used": result_data.get("tool_names_used", []),
        },
        success=result_data.get("success", True),
        error_msg=result_data.get("error"),
    )

    # Store successful tool usage in Milvus for self-improvement
    if result_data.get("success") and result_data.get("tool_names_used"):
        for idx, tool_name in enumerate(result_data["tool_names_used"]):
            params = result_data.get("tool_params_used", [])[idx] if idx < len(result_data.get("tool_params_used", [])) else {}
            await milvus_service.store_tool_usage(
                question=req.question,
                tool_name=tool_name,
                tool_params=params,
                user_id=user.id,
                username=user.username,
                success=True,
            )

    return QueryResponse(
        id=0,
        question=req.question,
        sql=result_data.get("sql"),
        result=result_data.get("result"),
        explanation=result_data.get("explanation"),
        chart_data=result_data.get("chart_data"),
        success=result_data.get("success", True),
        error=result_data.get("error"),
    )


@router.post("/execute-sql")
async def execute_sql_direct(
    sql: str,
    db_connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Direct SQL execution (for advanced users)."""
    if not check_tool_permission(user, "execute_sql_direct"):
        raise HTTPException(status_code=403, detail="无权执行直接SQL查询")

    result = await db.execute(select(DBConnection).where(DBConnection.id == db_connection_id))
    db_conn = result.scalar_one_or_none()
    if not db_conn:
        raise HTTPException(status_code=404, detail="数据库连接不存在")

    async with db_service.get_session(db_conn) as target_session:
        from sqlalchemy import text
        r = await target_session.execute(text(sql))
        cols = list(r.keys()) if r.returns_rows else []
        rows = [list(row) for row in r.fetchall()] if r.returns_rows else []
        await target_session.commit()

    await log_action(db, user.id, user.username, "execute_sql_direct",
                     detail=sql, success=True)

    return {"columns": cols, "rows": rows, "row_count": len(rows)}


api_router.include_router(router)
