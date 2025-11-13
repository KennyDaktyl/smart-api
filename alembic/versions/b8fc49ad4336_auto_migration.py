"""auto migration

Revision ID: b8fc49ad4336
Revises: 6385f226187d
Create Date: 2025-11-10 13:46:09.554356
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8fc49ad4336"
down_revision: Union[str, Sequence[str], None] = "6385f226187d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ✅ Utwórz typ ENUM, jeśli jeszcze nie istnieje
    devicemode = sa.Enum("MANUAL", "AUTO_POWER", "SCHEDULE", name="devicemode")
    devicemode.create(op.get_bind(), checkfirst=True)

    # ✅ Zmień kolumnę z VARCHAR na ENUM z jawnym rzutowaniem
    op.execute(
        """
        ALTER TABLE devices 
        ALTER COLUMN mode TYPE devicemode 
        USING mode::text::devicemode;
        """
    )


def downgrade() -> None:
    # ✅ Przywróć kolumnę do VARCHAR
    op.execute(
        """
        ALTER TABLE devices 
        ALTER COLUMN mode TYPE VARCHAR 
        USING mode::text;
        """
    )

    # ✅ Usuń typ ENUM (jeśli istnieje)
    devicemode = sa.Enum("MANUAL", "AUTO_POWER", "SCHEDULE", name="devicemode")
    devicemode.drop(op.get_bind(), checkfirst=True)
