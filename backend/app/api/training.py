"""Training data API - DDL, Schema, Documentation, SQL Examples."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.user import User
from app.models.training import TrainingData, TrainingType
from app.models.db_connection import DBConnection
from app.schemas.training import TrainingCreate, TrainingResponse
from app.core.auth import get_current_user
from app.core.permissions import check_tool_permission
from app.core.audit import log_action
from app.services.db_service import db_service
from app.api import api_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["训练"])


@router.post("/", response_model=TrainingResponse)
async def add_training(
    data: TrainingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add training data: DDL, Schema, Documentation, or SQL Example."""
    if not check_tool_permission(user, "add_training_data"):
        raise HTTPException(status_code=403, detail="仅管理员可添加训练数据")

    if data.training_type not in ("ddl", "schema", "documentation", "sql_example"):
        raise HTTPException(status_code=400, detail="无效的训练类型")

    if data.training_type == "sql_example" and (not data.question or not data.sql):
        raise HTTPException(status_code=400, detail="SQL示例需同时提供question和sql")

    record = TrainingData(
        training_type=data.training_type,
        db_connection_id=data.db_connection_id,
        content=data.content,
        description=data.description,
        question=data.question,
        sql=data.sql,
        created_by=user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await log_action(
        db, user.id, user.username, "training_add",
        tool_name="add_training_data",
        detail=f"{data.training_type}: {data.content[:200]}",
        success=True,
    )
    return record


@router.get("/", response_model=list[TrainingResponse])
async def list_trainings(
    db_connection_id: int | None = None,
    training_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List training data records."""
    query = select(TrainingData)
    if db_connection_id:
        query = query.where(TrainingData.db_connection_id == db_connection_id)
    if training_type:
        query = query.where(TrainingData.training_type == training_type)

    result = await db.execute(query.order_by(TrainingData.created_at.desc()))
    return result.scalars().all()


@router.delete("/{training_id}")
async def delete_training(
    training_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a training record."""
    if not check_tool_permission(user, "add_training_data"):
        raise HTTPException(status_code=403, detail="仅管理员可删除训练数据")

    result = await db.execute(select(TrainingData).where(TrainingData.id == training_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="训练数据不存在")

    await db.delete(record)
    await db.commit()

    await log_action(db, user.id, user.username, "training_delete",
                     detail=f"deleted training_id={training_id}", success=True)
    return {"message": "删除成功"}


@router.post("/auto-schema")
async def auto_import_schema(
    db_connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """一键训练：从 INFORMATION_SCHEMA 自动提取 Schema 和 DDL，类似 vanna 方式."""
    if not check_tool_permission(user, "add_training_data"):
        raise HTTPException(status_code=403, detail="仅管理员可导入Schema")

    result = await db.execute(select(DBConnection).where(DBConnection.id == db_connection_id))
    db_conn = result.scalar_one_or_none()
    if not db_conn:
        raise HTTPException(status_code=404, detail="数据库连接不存在")

    # 清除该数据源的旧训练数据
    await db.execute(delete(TrainingData).where(TrainingData.db_connection_id == db_connection_id))

    async with db_service.get_session(db_conn) as target_session:
        from sqlalchemy import text

        # 1. 获取完整 schema
        schema_info = await db_service.get_schema(db_conn)

        # 2. 获取表行数统计
        table_names = list(set(c["table_name"] for c in schema_info))
        row_counts = {}
        for t in table_names:
            try:
                if db_conn.db_type == "postgresql":
                    r = await target_session.execute(text(f'SELECT COUNT(*) FROM "{t}"'))
                else:
                    r = await target_session.execute(text(f"SELECT COUNT(*) FROM `{t}`"))
                row_counts[t] = r.scalar()
            except Exception:
                row_counts[t] = "未知"

    count = 0

    # 生成 DDL 语句
    tables_schema = {}
    for col in schema_info:
        t = col["table_name"]
        if t not in tables_schema:
            tables_schema[t] = []
        nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
        tables_schema[t].append(f'    {col["column_name"]} {col["data_type"]} {nullable}')

    for table_name, columns in tables_schema.items():
        ddl = f'CREATE TABLE "{table_name}" (\n' + ",\n".join(columns) + "\n);"
        record = TrainingData(
            training_type=TrainingType.DDL,
            db_connection_id=db_connection_id,
            content=ddl,
            description=f"表 {table_name}，约 {row_counts.get(table_name, '?')} 行",
            created_by=user.id,
        )
        db.add(record)
        count += 1

    # 生成 Schema 汇总文档
    schema_doc = "## 数据库表结构汇总\n\n"
    for table_name, columns in tables_schema.items():
        schema_doc += f"### {table_name}（约 {row_counts.get(table_name, '?')} 行）\n"
        for col in schema_info:
            if col["table_name"] == table_name:
                schema_doc += f"- **{col['column_name']}**: {col['data_type']}\n"
        schema_doc += "\n"

    record = TrainingData(
        training_type=TrainingType.DOCUMENTATION,
        db_connection_id=db_connection_id,
        content=schema_doc,
        description=f"完整数据库结构文档，共 {len(tables_schema)} 张表",
        created_by=user.id,
    )
    db.add(record)
    count += 1

    await db.commit()
    await log_action(db, user.id, user.username, "training_auto_schema",
                     detail=f"trained {len(tables_schema)} tables + 1 doc from db_connection_id={db_connection_id}",
                     success=True)
    return {
        "message": f"训练完成：{len(tables_schema)} 张表 DDL + 1 份文档",
        "table_count": len(tables_schema),
        "ddl_count": len(tables_schema),
    }


api_router.include_router(router)
