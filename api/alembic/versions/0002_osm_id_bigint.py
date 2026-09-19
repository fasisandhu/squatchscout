"""Widen leads.osm_id from INTEGER to BIGINT.

OpenStreetMap node ids passed 2^31 long ago: the first real production search for
dentists in Austin returned 54 businesses and persisted 5, because every candidate whose
node id was above 2,147,483,647 hit `psycopg.errors.NumericValueOutOfRange` on flush.
The per-lead error guard caught each one and logged `lead.failed`, so the search reported
success while quietly dropping 49 leads.

SQLite stores integers at whatever width they need, so the entire test suite passed
against it. Only Postgres enforces the declared column width.

Revision ID: 8f2c14a7d3e1
Revises: b1780eb594d6
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8f2c14a7d3e1"
down_revision: str | Sequence[str] | None = "b1780eb594d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table so this also applies on SQLite, which cannot ALTER a column type
    # in place and needs the table rebuilt around it.
    with op.batch_alter_table("leads") as batch:
        batch.alter_column(
            "osm_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Narrowing back will fail on any row whose osm_id exceeds 2^31, which is most of them.
    # That is correct: the old column could not hold this data.
    with op.batch_alter_table("leads") as batch:
        batch.alter_column(
            "osm_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
