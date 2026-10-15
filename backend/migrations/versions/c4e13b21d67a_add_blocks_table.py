"""Add Krakow GTFS blocks table.

Revision ID: c4e13b21d67a
Revises: 2d3a7c98b641
Create Date: 2026-10-15 23:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e13b21d67a"
down_revision: str | Sequence[str] | None = "2d3a7c98b641"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the blocks table used by the Krakow T feed."""
    op.create_table(
        "blocks",
        sa.Column("block_id", sa.Text(), nullable=False),
        sa.Column("shift", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("block_id"),
    )


def downgrade() -> None:
    """Drop the blocks table."""
    op.drop_table("blocks")
