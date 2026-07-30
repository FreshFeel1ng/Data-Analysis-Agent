"""Agent tools for text-to-SQL analysis."""

from langchain_core.tools import tool
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import traceback
import logging

logger = logging.getLogger(__name__)


class ExecuteSQLInput(BaseModel):
    sql: str = Field(description="The SQL query to execute on the target database")


class GetSchemaInput(BaseModel):
    table_name: Optional[str] = Field(default=None, description="Optional specific table name to filter")


class GetTableSampleInput(BaseModel):
    table_name: str = Field(description="Table name to sample from")
    limit: int = Field(default=5, description="Number of rows to return")


class RunPlottingCodeInput(BaseModel):
    data_json: str = Field(description="JSON output from execute_sql tool, e.g. {\"columns\":[...],\"rows\":[[...]]}")
    code: str = Field(description="Matplotlib/seaborn Python code using pre-loaded 'df' DataFrame")


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
                # Convert all values to Python native types for JSON serialization
                clean_rows = []
                for row in rows[:200]:
                    clean_rows.append([None if r is None else (float(r) if isinstance(r, (int, float)) else str(r)) for r in row])
                data = {
                    "columns": columns,
                    "rows": clean_rows,
                    "row_count": len(rows),
                }
            else:
                data = {"columns": [], "rows": [], "row_count": 0, "message": "Query executed (no rows returned)"}
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
            data = {"columns": columns, "rows": [list(r) for r in rows]}
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def run_plotting_code(self, data_json: str, code: str) -> str:
        """Execute LLM-generated Python plotting code with the given data."""
        logger.info(f"[Tool] run_plotting_code:\n{code[:200]}...")

        try:
            # Parse data into DataFrame
            data = json.loads(data_json)
            if "columns" in data and "rows" in data:
                df = pd.DataFrame(data["rows"], columns=data["columns"])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                return json.dumps({"error": "数据格式无法解析，请使用 execute_sql 返回的 JSON"})

            # Convert numeric columns
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass

            # Set Chinese font
            plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
            plt.rcParams["axes.unicode_minus"] = False

            # Execute LLM code in sandboxed namespace
            namespace = {
                "pd": pd,
                "plt": plt,
                "sns": sns,
                "df": df,
                "np": __import__("numpy"),
            }

            # Ensure figure creation
            if "plt.figure" not in code and "plt.subplots" not in code:
                full_code = "plt.figure(figsize=(10, 6))\n" + "sns.set_style('whitegrid')\n" + code + "\nplt.tight_layout()"
            else:
                full_code = code + "\nplt.tight_layout()"

            exec(full_code, namespace)

            # Check if a figure was created
            fig = plt.gcf()
            if len(fig.axes) == 0:
                return json.dumps({"error": "代码执行完毕但没有生成图表，请检查代码"})

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
            plt.close("all")
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode()

            return json.dumps({
                "image_base64": img_b64,
                "success": True,
            })
        except Exception as e:
            logger.exception("Plotting code execution failed")
            return json.dumps({
                "error": f"代码执行失败: {str(e)}\n\n{traceback.format_exc()}"
            })

    async def get_similar_examples(self, question: str) -> str:
        """Search Milvus for similar past tool usage examples."""
        logger.info(f"[Tool] get_similar_examples: {question[:100]}")
        examples = await self._milvus.search_similar_examples(question, top_k=5)
        return json.dumps(examples, ensure_ascii=False, default=str)


tool_registry = ToolRegistry()
