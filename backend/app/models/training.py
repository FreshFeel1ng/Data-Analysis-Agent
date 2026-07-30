from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SAEnum
from sqlalchemy.sql import func
from app.database import Base
import enum


class TrainingType(str, enum.Enum):
    DDL = "ddl"
    SCHEMA = "schema"
    DOCUMENTATION = "documentation"
    SQL_EXAMPLE = "sql_example"


class TrainingData(Base):
    __tablename__ = "training_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    training_type = Column(
        SAEnum(TrainingType, name="training_type_enum", create_type=False),
        nullable=False,
        default=TrainingType.DDL,
    )
    db_connection_id = Column(Integer, nullable=True, index=True)
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    question = Column(Text, nullable=True)  # for sql_example type
    sql = Column(Text, nullable=True)  # for sql_example type
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
