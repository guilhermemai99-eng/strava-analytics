"""Direct-message models: conversations, participants, messages."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Conversation(Base):
    """1:1 private thread. pair_key = f\"{min_id}:{max_id}\" prevents duplicates."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_key = Column(String(64), nullable=False, unique=True, index=True)
    conversation_type = Column(
        String(16),
        nullable=False,
        default="direct",
        server_default="direct",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    last_message_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_participant",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    read_at = Column(DateTime(timezone=True), nullable=True)
