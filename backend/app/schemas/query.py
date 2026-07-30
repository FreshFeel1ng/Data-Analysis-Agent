from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class QueryRequest(BaseModel):
    question: str
    db_connection_id: int


class QueryResponse(BaseModel):
    id: int
    question: str
    sql: Optional[str] = None
    result: Optional[Any] = None
    explanation: Optional[str] = None
    chart_type: Optional[str] = None
    chart_data: Optional[Any] = None
    success: bool
    error: Optional[str] = None
    created_at: Optional[datetime] = None
