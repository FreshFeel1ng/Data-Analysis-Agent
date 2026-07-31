from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    db_connection_id = Column(Integer, nullable=True)
    db_name = Column(String(100), nullable=True)
    question = Column(Text, nullable=False)
    sql = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    chart_data = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
