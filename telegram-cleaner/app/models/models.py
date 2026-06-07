"""
Database models for Telegram Cleaner.
Uses SQLAlchemy ORM with async SQLite support.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserSession(Base):
    """Stores active user sessions."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    session_string = Column(Text, nullable=True)  # Telethon StringSession
    api_id = Column(Integer, nullable=True)
    api_hash = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatRecord(Base):
    """Cached record of a Telegram chat (group/channel/supergroup)."""
    __tablename__ = "chat_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False)
    chat_type = Column(String(20), nullable=False)  # group, channel, supergroup, megagroup
    username = Column(String(100), nullable=True)
    member_count = Column(Integer, nullable=True)
    unread_count = Column(Integer, default=0)
    is_muted = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    photo_path = Column(String(255), nullable=True)
    is_kept = Column(Boolean, default=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())


class CleanupLog(Base):
    """Logs of cleanup operations performed."""
    __tablename__ = "cleanup_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    chat_name = Column(String(255), nullable=False)
    action = Column(String(20), nullable=False)   # left, failed, skipped
    error_message = Column(Text, nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
