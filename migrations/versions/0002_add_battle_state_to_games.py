"""add battle state to games

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24 14:05:41.805413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "games",
        sa.Column("opponent_shots", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "games",
        sa.Column("my_shots", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("games", "my_shots")
    op.drop_column("games", "opponent_shots")
