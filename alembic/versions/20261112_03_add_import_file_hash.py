"""Protect ETL imports from repeated files per source profile.

Revision ID: 20261112_03
Revises: 20261112_02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261112_03"
down_revision: Union[str, Sequence[str], None] = "20261112_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "importaciones_etl",
        sa.Column("hash_archivo", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_importaciones_etl_hash_perfil",
        "importaciones_etl",
        ["hash_archivo", "perfil_fuente"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_importaciones_etl_hash_perfil",
        "importaciones_etl",
        type_="unique",
    )
    op.drop_column("importaciones_etl", "hash_archivo")
