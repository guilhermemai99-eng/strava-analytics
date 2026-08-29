"""Add direct-message tables (conversations, participants, messages).

Revision ID: 0009_direct_messages
Revises: 0008_follows
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0009_direct_messages"
down_revision = "0008_follows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pair_key", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.UniqueConstraint("pair_key", name="uq_conversations_pair_key"),
    )
    op.create_index("ix_conversations_pair_key", "conversations", ["pair_key"])
    op.create_index(
        "ix_conversations_last_message_at",
        "conversations",
        ["last_message_at"],
    )

    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("athletes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_participant",
        ),
    )
    op.create_index(
        "ix_conversation_participants_conversation_id",
        "conversation_participants",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_participants_user_id",
        "conversation_participants",
        ["user_id"],
    )

    op.create_table(
        "direct_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.Integer(),
            sa.ForeignKey("athletes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_direct_messages_conversation_id",
        "direct_messages",
        ["conversation_id"],
    )
    op.create_index(
        "ix_direct_messages_sender_id",
        "direct_messages",
        ["sender_id"],
    )
    op.create_index(
        "ix_direct_messages_created_at",
        "direct_messages",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_direct_messages_created_at", table_name="direct_messages")
    op.drop_index("ix_direct_messages_sender_id", table_name="direct_messages")
    op.drop_index(
        "ix_direct_messages_conversation_id", table_name="direct_messages"
    )
    op.drop_table("direct_messages")
    op.drop_index(
        "ix_conversation_participants_user_id",
        table_name="conversation_participants",
    )
    op.drop_index(
        "ix_conversation_participants_conversation_id",
        table_name="conversation_participants",
    )
    op.drop_table("conversation_participants")
    op.drop_index(
        "ix_conversations_last_message_at", table_name="conversations"
    )
    op.drop_index("ix_conversations_pair_key", table_name="conversations")
    op.drop_table("conversations")
