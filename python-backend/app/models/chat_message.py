from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, func

from .database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column("document_id", Integer, nullable=False)
    sender_id = Column("sender_id", Integer, nullable=False)
    message = Column(Text, nullable=False)
    message_type = Column("message_type", String(20), nullable=False, default="TEXT")
    created_at = Column(DateTime, default=datetime.now, server_default=func.now())
