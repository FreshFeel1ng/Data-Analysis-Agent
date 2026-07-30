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
import io
import base64
import logging

logger = logging.getLogger(__name__)


class ExecuteSQLInput(BaseModel):
    sql: str = Field(description="The SQL query to execute on the target database")


class GetSchemaInput(BaseModel):
    table_name: Optional[str] = Field(default=None, description="Optional specific table name to filter")


class GenerateChartInput(BaseModel):
    data_json: str = Field(description="JSON serialized table data with columns and rows")
    chart_type: str = Field(
        description="Chart type: bar, line, pie, scatter, histogram, heatmap"
    )
    title: str = Field(description="Chart title")
    x_column: Optional[str] = Field(default=None, description="Column for X axis")
    y_column: Optional[str] = Field(default=None, description="Column for Y axis")


class GetSimilarExamplesInput(BaseModel):
    question: str = Field(description="The user's question to find similar past examples for")


class ToolRegistry:
    """Manages tool instances with DB context injection."""

    def __init__(self):
        self._db_session = None  # target DB session
        self._app_db = None  # app PostgreSQL session
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
                data = {"columns": columns, "rows": [list(r) for r in rows][:200], "row_count": len(rows)}
            else:
                data = {"columns": [], "rows": [], "row_count": 0, "message": "Query executed (no rows returned)"}
            await self._db_session.commit()
            return json.dumps(data, ensure_ascii=False, default=str)
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

            return json.dumps(schema, ensure_ascii=False, default=str)
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

    def generate_chart(
        self, data_json: str, chart_type: str, title: str,
        x_column: Optional[str] = None, y_column: Optional[str] = None
    ) -> str:
        """Generate a chart image from data."""
        logger.info(f"[Tool] generate_chart: {chart_type} - {title}")
        try:
            data = json.loads(data_json)

            # Support multiple data formats
            if isinstance(data, list):
                # [{col: val, ...}, ...] → DataFrame
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                if "columns" in data and "rows" in data:
                    # {"columns": [...], "rows": [[...]]} → DataFrame
                    df = pd.DataFrame(data.get("rows", []), columns=data.get("columns", []))
                elif "data" in data:
                    # {"data": [...]} → DataFrame
                    inner = data["data"]
                    df = pd.DataFrame(inner)
                else:
                    # Flat dict → DataFrame with one row
                    df = pd.DataFrame([data])
            else:
                return json.dumps({"error": "无法解析数据格式"})

            if df.empty:
                return json.dumps({"error": "没有可绘图的数据"})

            # Auto-convert numeric columns
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass

            plt.figure(figsize=(10, 6))
            sns.set_style("whitegrid")
            # Set Chinese font AFTER sns.set_style to avoid override
            plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
            plt.rcParams["axes.unicode_minus"] = False

            if chart_type == "bar":
                x = x_column or df.columns[0]
                y = y_column or (df.columns[1] if len(df.columns) > 1 else df.columns[0])
                numeric_cols = df.select_dtypes(include="number").columns
                if y not in numeric_cols and len(numeric_cols) > 0:
                    y = numeric_cols[0]
                sns.barplot(data=df, x=x, y=y)

            elif chart_type == "line":
                x = x_column or df.columns[0]
                y = y_column or (df.columns[1] if len(df.columns) > 1 else df.columns[0])
                plt.plot(df[x], df[y], marker="o")
                plt.xlabel(x)
                plt.ylabel(y)

            elif chart_type == "pie":
                label_col = x_column or df.columns[0]
                value_col = y_column or (df.columns[1] if len(df.columns) > 1 else df.columns[0])
                numeric_cols = df.select_dtypes(include="number").columns
                if value_col not in numeric_cols and len(numeric_cols) > 0:
                    value_col = numeric_cols[0]
                plt.pie(df[value_col], labels=df[label_col], autopct="%1.1f%%")

            elif chart_type == "scatter":
                x = x_column or df.columns[0]
                y = y_column or (df.columns[1] if len(df.columns) > 1 else df.columns[0])
                plt.scatter(df[x], df[y])

            elif chart_type == "histogram":
                col = x_column or df.select_dtypes(include="number").columns[0]
                plt.hist(df[col], bins=20, edgecolor="black")

            elif chart_type == "heatmap":
                numeric_df = df.select_dtypes(include="number")
                sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm", fmt=".2f")

            else:
                return json.dumps({"error": f"Unsupported chart type: {chart_type}"})

            plt.title(title, fontsize=14)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=60, bbox_inches="tight")
            plt.close()
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode()
            return json.dumps({"image_base64": img_b64, "chart_type": chart_type, "title": title})
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return json.dumps({"error": str(e)})

    async def get_similar_examples(self, question: str) -> str:
        """Search Milvus for similar past tool usage examples."""
        logger.info(f"[Tool] get_similar_examples: {question[:100]}")
        examples = await self._milvus.search_similar_examples(question, top_k=5)
        return json.dumps(examples, ensure_ascii=False, default=str)


tool_registry = ToolRegistry()
