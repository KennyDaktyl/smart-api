"""Add manual_state column to devices

Revision ID: 0b4f98b61c21
Revises: 9465b47bcad2
Create Date: 2025-12-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0b4f98b61c21"
down_revision: Union[str, Sequence[str], None] = "9465b47bcad2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("devices", sa.Column("manual_state", sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("devices", "manual_state")
