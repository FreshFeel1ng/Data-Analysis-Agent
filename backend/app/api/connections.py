"""DB Connection management API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.db_connection import DBConnection
from app.core.auth import get_current_user
from app.core.permissions import check_tool_permission
from app.core.audit import log_action
from app.schemas.training import DBConnectionCreate, DBConnectionResponse
from app.api import api_router

router = APIRouter(prefix="/connections", tags=["数据库连接"])


@router.post("/", response_model=DBConnectionResponse)
async def create_connection(
    data: DBConnectionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not check_tool_permission(user, "manage_db_connection"):
        raise HTTPException(status_code=403, detail="仅管理员可管理数据库连接")

    conn = DBConnection(
        name=data.name,
        db_type=data.db_type,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password_encrypted=data.password,  # TODO: encrypt password
        created_by=user.id,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    await log_action(db, user.id, user.username, "connection_create",
                     tool_name="manage_db_connection",
                     detail=f"{data.db_type}://{data.host}:{data.port}/{data.database}",
                     success=True)
    return conn


@router.get("/", response_model=list[DBConnectionResponse])
async def list_connections(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(DBConnection))
    return result.scalars().all()


@router.delete("/{conn_id}")
async def delete_connection(
    conn_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not check_tool_permission(user, "manage_db_connection"):
        raise HTTPException(status_code=403, detail="仅管理员可删除数据库连接")

    result = await db.execute(select(DBConnection).where(DBConnection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")

    await db.delete(conn)
    await db.commit()

    from app.services.db_service import db_service
    await db_service.close_engine(conn_id)

    await log_action(db, user.id, user.username, "connection_delete",
                     tool_name="manage_db_connection", success=True)
    return {"message": "删除成功"}


api_router.include_router(router)
