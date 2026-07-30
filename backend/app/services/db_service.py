import logging
from typing import Optional, Any, List, Dict
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, exc
from app.models.db_connection import DBConnection

logger = logging.getLogger(__name__)


class DatabaseService:
    """Manage connections to target databases (user's databases for querying)."""

    _engines: Dict[int, Any] = {}
    _sessions: Dict[int, Any] = {}

    def _build_url(self, conn: DBConnection) -> str:
        if conn.db_type == "postgresql":
            return (
                f"postgresql+asyncpg://{conn.username}:{conn.password_encrypted}"
                f"@{conn.host}:{conn.port}/{conn.database}"
            )
        elif conn.db_type == "mysql":
            return (
                f"mysql+aiomysql://{conn.username}:{conn.password_encrypted}"
                f"@{conn.host}:{conn.port}/{conn.database}"
            )
        raise ValueError(f"Unsupported db_type: {conn.db_type}")

    async def get_engine(self, conn: DBConnection):
        if conn.id not in self._engines:
            url = self._build_url(conn)
            engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=5)
            self._engines[conn.id] = engine
        return self._engines[conn.id]

    @asynccontextmanager
    async def get_session(self, conn: DBConnection):
        engine = await self.get_engine(conn)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def execute_query(self, conn: DBConnection, sql: str) -> tuple:
        """Execute SQL on target database. Returns (columns, rows)."""
        try:
            async with self.get_session(conn) as session:
                result = await session.execute(text(sql))
                columns = list(result.keys()) if result.returns_rows else []
                rows = [list(r) for r in result.fetchall()] if result.returns_rows else []
                await session.commit()
                return columns, rows
        except exc.SQLAlchemyError as e:
            logger.error(f"SQL execution error: {e}")
            raise

    async def get_schema(self, conn: DBConnection) -> List[Dict]:
        """Retrieve table schema from target database."""
        if conn.db_type == "postgresql":
            sql = """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_name, ordinal_position
            """
        elif conn.db_type == "mysql":
            sql = f"""
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = '{conn.database}'
                ORDER BY table_name, ordinal_position
            """
        else:
            return []

        try:
            async with self.get_session(conn) as session:
                result = await session.execute(text(sql))
                rows = result.fetchall()
                return [
                    {
                        "table_name": r[0],
                        "column_name": r[1],
                        "data_type": r[2],
                        "is_nullable": r[3],
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Schema retrieval failed: {e}")
            raise

    async def get_table_sample(self, conn: DBConnection, table_name: str, limit: int = 5) -> List[Dict]:
        """Get a sample of data from a table."""
        sql = f'SELECT * FROM "{table_name}" LIMIT {limit}' if conn.db_type == "postgresql" else f"SELECT * FROM `{table_name}` LIMIT {limit}"
        cols, rows = await self.execute_query(conn, sql)
        return [dict(zip(cols, row)) for row in rows]

    async def close_engine(self, conn_id: int):
        if conn_id in self._engines:
            await self._engines[conn_id].dispose()
            del self._engines[conn_id]


db_service = DatabaseService()
