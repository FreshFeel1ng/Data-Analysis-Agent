"""Agent tools for text-to-SQL analysis."""

from langchain_core.tools import tool
from typing import Optional
from pydantic import BaseModel, Field
import json
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages tool instances with DB context injection."""

    def __init__(self):
        self._db_session = None
        self._app_db = None
        self._db_conn = None
        self._user = None
        self._milvus = None

    def bind_context(self, db_session, app_db, db_conn, user, milvus):
        self._db_session = db_session
        self._app_db = app_db
        self._db_conn = db_conn
        self._user = user
        self._milvus = milvus

    async def execute_sql(self, sql: str) -> str:
        """Execute SQL on the connected database and return results."""
        from sqlalchemy import text

        logger.info(f"[Tool] execute_sql: {sql[:200]}...")
        try:
            result = await self._db_session.execute(text(sql))
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys())
                clean_rows = []
                for row in rows[:200]:
                    clean_rows.append([
                        None if r is None else (float(r) if isinstance(r, (int, float)) else str(r))
                        for r in row
                    ])
                data = {"columns": columns, "rows": clean_rows, "row_count": len(rows)}
            else:
                data = {"columns": [], "rows": [], "row_count": 0, "message": "Query executed"}
            await self._db_session.commit()
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return json.dumps({"error": str(e)})

    async def get_schema(self, table_name: Optional[str] = None) -> str:
        """Get database schema information."""
        from sqlalchemy import text

        logger.info(f"[Tool] get_schema: table={table_name}")
        try:
            db_type = self._db_conn.db_type
            if db_type == "postgresql":
                base_sql = """
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                """
            else:
                base_sql = f"""
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = '{self._db_conn.database}'
                """
            if table_name:
                base_sql += f" AND table_name = '{table_name}'"
            base_sql += " ORDER BY table_name, ordinal_position"

            result = await self._db_session.execute(text(base_sql))
            rows = result.fetchall()
            schema = {}
            for r in rows:
                t = r[0]
                if t not in schema:
                    schema[t] = []
                schema[t].append({"column": r[1], "type": r[2], "nullable": r[3]})
            return json.dumps(schema, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Schema retrieval failed: {e}")
            return json.dumps({"error": str(e)})

    async def get_table_sample(self, table_name: str, limit: int = 5) -> str:
        """Get sample data from a table."""
        from sqlalchemy import text

        logger.info(f"[Tool] get_table_sample: {table_name}")
        try:
            if self._db_conn.db_type == "postgresql":
                sql = f'SELECT * FROM "{table_name}" LIMIT {limit}'
            else:
                sql = f"SELECT * FROM `{table_name}` LIMIT {limit}"
            result = await self._db_session.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            return json.dumps({"columns": columns, "rows": [list(r) for r in rows]}, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def generate_chart(self, title: str, echarts_option: str) -> str:
        """Validate and return ECharts option JSON. LLM 生成此 JSON 配置，前端用 Apache ECharts 渲染."""
        logger.info(f"[Tool] generate_chart: {title}")
        try:
            option = json.loads(echarts_option)

            # Ensure required top-level fields
            if "title" not in option:
                option["title"] = {"text": title, "left": "center"}
            if "tooltip" not in option:
                option["tooltip"] = {}
            if "xAxis" not in option and "series" in option:
                option["xAxis"] = {"type": "category"}
            if "yAxis" not in option and "series" in option:
                option["yAxis"] = {"type": "value"}
            # Set default toolbox with save-as-image
            option.setdefault("toolbox", {
                "feature": {"saveAsImage": {"title": "下载"}},
                "right": 10
            })
            # Set default series label
            for s in option.get("series", []):
                if s.get("type") in ("bar", "line"):
                    s.setdefault("label", {"show": True, "position": "top"})

            return json.dumps({"echarts_option": option, "success": True}, ensure_ascii=False)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"ECharts JSON 格式错误: {str(e)}", "success": False})

    async def get_similar_examples(self, question: str) -> str:
        """Search Milvus for similar past tool usage examples."""
        logger.info(f"[Tool] get_similar_examples: {question[:100]}")
        examples = await self._milvus.search_similar_examples(question, top_k=5)
        return json.dumps(examples, ensure_ascii=False, default=str)


tool_registry = ToolRegistry()
