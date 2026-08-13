"""数据模型：分类 / 错题 / 对话 / 消息。"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    color = Column(String, default="#3B82F6")
    mistakes = relationship("Mistake", back_populates="category")


class Mistake(Base):
    __tablename__ = "mistakes"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), default=1)
    content = Column(Text, nullable=False)
    subject = Column(String, default="")
    knowledge_points = Column(JSON, default=list)
    source = Column(String, default="")
    review_count = Column(Integer, default=0)          # SM-2: repetitions（复习尝试次数）
    reviewed = Column(Boolean, default=False)
    ai_analysis = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    # ---- SM-2 记忆曲线字段（复习排程）----
    easiness_factor = Column(Float, default=2.5)        # EF，初始 2.5
    interval_days = Column(Integer, default=0)         # 下一次复习间隔（天）
    due_date = Column(DateTime, nullable=True)          # 应复习日期（None 表示未排程）
    category = relationship("Category", back_populates="mistakes")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship(
        "ChatMessage", back_populates="conversation", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")
