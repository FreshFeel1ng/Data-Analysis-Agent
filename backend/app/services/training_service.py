import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.training import TrainingData, TrainingType

logger = logging.getLogger(__name__)


async def get_training_context(
    db: AsyncSession, db_connection_id: int | None = None
) -> Dict[str, List[str]]:
    """Gather all training data as context for the LLM."""
    query = select(TrainingData)
    if db_connection_id:
        query = query.where(TrainingData.db_connection_id == db_connection_id)

    result = await db.execute(query)
    records = result.scalars().all()

    context: Dict[str, List[str]] = {
        "ddl": [],
        "schema": [],
        "documentation": [],
        "sql_examples": [],
    }

    for r in records:
        if r.training_type == TrainingType.DDL:
            context["ddl"].append(r.content)
        elif r.training_type == TrainingType.SCHEMA:
            context["schema"].append(r.content)
        elif r.training_type == TrainingType.DOCUMENTATION:
            context["documentation"].append(r.content)
        elif r.training_type == TrainingType.SQL_EXAMPLE:
            if r.question and r.sql:
                context["sql_examples"].append(f"Q: {r.question}\nSQL: {r.sql}")

    return context


def build_training_prompt(context: Dict[str, List[str]]) -> str:
    """Build a prompt section from training data."""
    parts = []

    if context["ddl"]:
        parts.append("## 数据库DDL语句\n" + "\n\n".join(context["ddl"]))

    if context["schema"]:
        parts.append("## 数据库Schema信息\n" + "\n\n".join(context["schema"]))

    if context["documentation"]:
        parts.append("## 业务术语和指标定义\n" + "\n\n".join(context["documentation"]))

    if context["sql_examples"]:
        parts.append("## 参考SQL示例\n" + "\n\n".join(context["sql_examples"]))

    return "\n\n".join(parts)
