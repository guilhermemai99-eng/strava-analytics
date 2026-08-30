from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(
        Integer,
        ForeignKey("athletes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind = Column(String(32), nullable=False, index=True)
    body = Column(Text, nullable=False)
    # Optional link target: conversation id, athlete id, etc.
    target_type = Column(String(32), nullable=True)
    target_id = Column(Integer, nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
