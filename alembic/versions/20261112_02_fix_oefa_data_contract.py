"""Fix OEFA textual municipality field contract.

Revision ID: 20261112_02
Revises: 20261112_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261112_02"
down_revision: Union[str, Sequence[str], None] = "20261112_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "areas_degradadas_oefa",
        "municipalidad_disponen",
        existing_type=sa.Numeric(18, 3),
        type_=sa.String(1000),
        existing_nullable=True,
        postgresql_using="municipalidad_disponen::text",
    )


def downgrade() -> None:
    """Revert only when existing text values are numeric or empty.

    Real OEFA municipality names cannot be represented by the old numeric
    column, so the downgrade must stop instead of silently discarding them.
    """
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM areas_degradadas_oefa
                    WHERE municipalidad_disponen IS NOT NULL
                      AND btrim(municipalidad_disponen) <> ''
                      AND btrim(municipalidad_disponen) !~ '^[+-]?([0-9]+([.][0-9]+)?|[.][0-9]+)$'
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade municipalidad_disponen: non-numeric text exists';
                END IF;
            END $$;
            """
        )
    )
    op.alter_column(
        "areas_degradadas_oefa",
        "municipalidad_disponen",
        existing_type=sa.String(1000),
        type_=sa.Numeric(18, 3),
        existing_nullable=True,
        postgresql_using="NULLIF(municipalidad_disponen, '')::numeric",
    )
