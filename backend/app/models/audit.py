from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)  # query, tool_call, login, training
    tool_name = Column(String(100), nullable=True)
    resource = Column(String(255), nullable=True)  # db_name.table_name
    detail = Column(Text, nullable=True)  # SQL query or parameters
    params = Column(JSON, nullable=True)  # tool parameters
    ip_address = Column(String(50), nullable=True)
    success = Column(Boolean, default=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
