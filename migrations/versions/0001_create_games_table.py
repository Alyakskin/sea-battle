"""create games table

Revision ID: 0001
Revises: 
Create Date: 2026-09-14 10:14:27.066538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "games",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("ships", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("games")
