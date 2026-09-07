"""make timestamp columns timezone-aware

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# `models.py`'s `_now()` returns timezone-aware UTC datetimes, but `0001_initial_schema.py` created
# these columns as `TIMESTAMP WITHOUT TIME ZONE` (SQLAlchemy's `DateTime()` default). asyncpg
# refuses to insert an aware datetime into a naive column, so every INSERT/UPDATE touching these
# columns fails on Postgres. SQLite has no concept of a timezone-aware column type (it stores
# datetimes as plain text either way), so this migration only needs to run on Postgres.

_COLUMNS = [
    ("users", "created_at"),
    ("conversations", "created_at"),
    ("conversations", "updated_at"),
    ("messages", "created_at"),
    ("uploaded_files", "uploaded_at"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
