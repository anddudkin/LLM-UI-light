"""cascade delete: conversation -> messages -> uploaded_files

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQLite doesn't support ALTER-ing an existing foreign key constraint (would need Alembic's
# batch/table-rebuild mode); on sqlite the delete cascade is enforced at the SQLAlchemy ORM level
# instead (see the `cascade="all, delete-orphan"` relationships in models.py), so this migration
# only touches Postgres. It targets Postgres's default auto-generated constraint names
# (<table>_<column>_fkey), which is what `0001_initial_schema.py` produced since it didn't name
# these constraints explicitly.


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint("messages_conversation_id_fkey", "messages", type_="foreignkey")
    op.create_foreign_key(
        "messages_conversation_id_fkey",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("uploaded_files_message_id_fkey", "uploaded_files", type_="foreignkey")
    op.create_foreign_key(
        "uploaded_files_message_id_fkey",
        "uploaded_files",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint("uploaded_files_message_id_fkey", "uploaded_files", type_="foreignkey")
    op.create_foreign_key(
        "uploaded_files_message_id_fkey", "uploaded_files", "messages", ["message_id"], ["id"]
    )

    op.drop_constraint("messages_conversation_id_fkey", "messages", type_="foreignkey")
    op.create_foreign_key(
        "messages_conversation_id_fkey", "messages", "conversations", ["conversation_id"], ["id"]
    )
