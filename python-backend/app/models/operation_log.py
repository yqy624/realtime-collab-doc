from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, DateTime, Text, func

from .database import Base


class OperationType(str, PyEnum):
    INSERT = "INSERT"
    DELETE = "DELETE"
    FULL_SYNC = "FULL_SYNC"


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column("document_id", Integer, nullable=False)
    user_id = Column("user_id", Integer, nullable=False)
    operation_type = Column("operation_type", String(20), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    content = Column(Text, default="")
    revision = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
