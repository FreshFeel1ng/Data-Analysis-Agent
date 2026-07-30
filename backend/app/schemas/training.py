from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TrainingCreate(BaseModel):
    training_type: str  # ddl | schema | documentation | sql_example
    db_connection_id: Optional[int] = None
    content: str
    description: Optional[str] = None
    question: Optional[str] = None  # for sql_example
    sql: Optional[str] = None  # for sql_example


class TrainingResponse(BaseModel):
    id: int
    training_type: str
    db_connection_id: Optional[int] = None
    content: str
    description: Optional[str] = None
    question: Optional[str] = None
    sql: Optional[str] = None
    created_by: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DBConnectionCreate(BaseModel):
    name: str
    db_type: str  # postgresql | mysql
    host: str
    port: int
    database: str
    username: str
    password: str


class DBConnectionResponse(BaseModel):
    id: int
    name: str
    db_type: str
    host: str
    port: int
    database: str
    username: str
    is_active: bool
    created_by: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
