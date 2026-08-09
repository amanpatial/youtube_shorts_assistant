"""phase17_owner_key_id

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-05 20:10:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("workflows")}
    if "owner_key_id" not in cols:
        op.add_column(
            "workflows",
            sa.Column("owner_key_id", sa.String(length=32), nullable=True),
        )
        op.create_index("ix_workflows_owner_key_id", "workflows", ["owner_key_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("workflows")}
    if "owner_key_id" in cols:
        op.drop_index("ix_workflows_owner_key_id", table_name="workflows")
        op.drop_column("workflows", "owner_key_id")
