"""phase11_memory_items

Revision ID: a1b2c3d4e5f6
Revises: 9e5111c3fcf7
Create Date: 2026-08-04 22:55:00.000000

Idempotent: local DX uses ``ensure_schema()`` / ``create_all``, which may create
``memory_items`` before Alembic records this revision.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9e5111c3fcf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "memory_items" not in inspector.get_table_names():
        op.create_table(
            "memory_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("kind", sa.String(length=64), nullable=False),
            sa.Column("topic", sa.Text(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("embedding", sa.JSON(), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column("execution_id", sa.Uuid(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    existing = {ix["name"] for ix in inspector.get_indexes("memory_items")}
    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        if "ix_memory_items_kind" not in existing:
            batch_op.create_index(
                batch_op.f("ix_memory_items_kind"), ["kind"], unique=False
            )
        if "ix_memory_items_execution_id" not in existing:
            batch_op.create_index(
                batch_op.f("ix_memory_items_execution_id"),
                ["execution_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "memory_items" not in inspector.get_table_names():
        return
    existing = {ix["name"] for ix in inspector.get_indexes("memory_items")}
    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        if "ix_memory_items_execution_id" in existing:
            batch_op.drop_index(batch_op.f("ix_memory_items_execution_id"))
        if "ix_memory_items_kind" in existing:
            batch_op.drop_index(batch_op.f("ix_memory_items_kind"))
    op.drop_table("memory_items")
