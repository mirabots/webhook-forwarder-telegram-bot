"""initial

Revision ID: 0876cf58e74b
Revises:
Create Date: 2023-11-12 22:00:17.350367

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0876cf58e74b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "chats",
        sa.Column("id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column("owner_id", sa.BIGINT(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="wftb",
    )
    op.create_table(
        "targets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("webhook", sa.Text(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("chat_id", sa.BIGINT(), nullable=False),
        sa.Column("key", sa.String(), nullable=True),
        sa.Column("prefix", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("webhook"),
        schema="wftb",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("targets", schema="wftb")
    op.drop_table("chats", schema="wftb")
    # ### end Alembic commands ###
