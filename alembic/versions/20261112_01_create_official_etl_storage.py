"""Create ETL audit and official dataset storage tables.

Revision ID: 20261112_01
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261112_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "importaciones_etl",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("tipo_archivo", sa.String(length=20), nullable=False),
        sa.Column("perfil_fuente", sa.String(length=80), nullable=True),
        sa.Column("entidad_fuente", sa.String(length=150), nullable=True),
        sa.Column(
            "fecha_importacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("total_filas_procesadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_filas_validas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_filas_rechazadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="pendiente"),
        sa.Column("mensaje_error", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'procesando', 'completado', 'fallido')",
            name="ck_importaciones_etl_estado",
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    )

    op.create_table(
        "registros_rechazados_etl",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("importacion_id", sa.Integer(), nullable=False),
        sa.Column("numero_fila", sa.Integer(), nullable=False),
        sa.Column("datos_originales", sa.JSON(), nullable=False),
        sa.Column("motivo_rechazo", sa.String(length=1000), nullable=False),
        sa.Column(
            "fecha_registro",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["importacion_id"], ["importaciones_etl.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_registros_rechazados_importacion",
        "registros_rechazados_etl",
        ["importacion_id"],
    )

    op.create_table(
        "generacion_residuos_distrito_anual",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("importacion_id", sa.Integer(), nullable=False),
        sa.Column("perfil_fuente", sa.String(length=80), nullable=False),
        sa.Column("ubigeo", sa.String(length=10), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("departamento", sa.String(length=120), nullable=True),
        sa.Column("provincia", sa.String(length=120), nullable=True),
        sa.Column("distrito", sa.String(length=120), nullable=True),
        sa.Column("poblacion_total_inei", sa.Numeric(18, 3), nullable=True),
        sa.Column("poblacion_urbana_inei", sa.Numeric(18, 3), nullable=True),
        sa.Column("poblacion_rural_inei", sa.Numeric(18, 3), nullable=True),
        sa.Column("generacion_per_capita_domiciliaria", sa.Numeric(18, 6), nullable=True),
        sa.Column("generacion_domiciliaria_urbana_t_dia", sa.Numeric(18, 6), nullable=True),
        sa.Column("generacion_domiciliaria_urbana_t_anio", sa.Numeric(18, 6), nullable=True),
        sa.Column("generacion_municipal_t_anio", sa.Numeric(18, 6), nullable=True),
        sa.Column("generacion_municipal_t_dia", sa.Numeric(18, 6), nullable=True),
        sa.Column("generacion_per_capita_municipal", sa.Numeric(18, 6), nullable=True),
        sa.Column("datos_originales", postgresql.JSONB(), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["importacion_id"], ["importaciones_etl.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_generacion_residuos_ubigeo",
        "generacion_residuos_distrito_anual",
        ["ubigeo"],
    )
    op.create_index(
        "ix_generacion_residuos_anio",
        "generacion_residuos_distrito_anual",
        ["anio"],
    )
    op.create_index(
        "ix_generacion_residuos_importacion",
        "generacion_residuos_distrito_anual",
        ["importacion_id"],
    )

    op.create_table(
        "areas_degradadas_oefa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("importacion_id", sa.Integer(), nullable=False),
        sa.Column("perfil_fuente", sa.String(length=80), nullable=False),
        sa.Column("ubigeo", sa.String(length=10), nullable=True),
        sa.Column("id_uf", sa.String(length=100), nullable=True),
        sa.Column("municipalidad_administradora", sa.String(length=255), nullable=True),
        sa.Column("denominacion", sa.String(length=255), nullable=True),
        sa.Column("zona", sa.String(length=150), nullable=True),
        sa.Column("este", sa.Numeric(18, 6), nullable=True),
        sa.Column("norte", sa.Numeric(18, 6), nullable=True),
        sa.Column("perimetro", sa.Numeric(18, 6), nullable=True),
        sa.Column("area_m2", sa.Numeric(18, 6), nullable=True),
        sa.Column("area_ha", sa.Numeric(18, 6), nullable=True),
        sa.Column("municipalidad_disponen", sa.Numeric(18, 3), nullable=True),
        sa.Column("cantidad_municipalidades_disponen", sa.Numeric(18, 3), nullable=True),
        sa.Column("segregacion", sa.Boolean(), nullable=True),
        sa.Column("crianza_animal", sa.Boolean(), nullable=True),
        sa.Column("quema_rrss", sa.Boolean(), nullable=True),
        sa.Column("rrss_salud", sa.Boolean(), nullable=True),
        sa.Column("rrss_industrial", sa.Boolean(), nullable=True),
        sa.Column("natural_aguajal", sa.Boolean(), nullable=True),
        sa.Column("natural_bofedal", sa.Boolean(), nullable=True),
        sa.Column("natural_pantano", sa.Boolean(), nullable=True),
        sa.Column("amortiguamiento_anp", sa.Boolean(), nullable=True),
        sa.Column("anp", sa.Boolean(), nullable=True),
        sa.Column("categoria", sa.String(length=150), nullable=True),
        sa.Column("anio_incorporacion", sa.Integer(), nullable=True),
        sa.Column("fecha_corte", sa.Date(), nullable=True),
        sa.Column("datos_originales", postgresql.JSONB(), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["importacion_id"], ["importaciones_etl.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_areas_degradadas_ubigeo", "areas_degradadas_oefa", ["ubigeo"])
    op.create_index("ix_areas_degradadas_importacion", "areas_degradadas_oefa", ["importacion_id"])
    op.create_index("ix_areas_degradadas_id_uf", "areas_degradadas_oefa", ["id_uf"])
    op.create_index(
        "ix_areas_degradadas_fecha_corte", "areas_degradadas_oefa", ["fecha_corte"]
    )


def downgrade() -> None:
    op.drop_index("ix_areas_degradadas_fecha_corte", table_name="areas_degradadas_oefa")
    op.drop_index("ix_areas_degradadas_id_uf", table_name="areas_degradadas_oefa")
    op.drop_index("ix_areas_degradadas_importacion", table_name="areas_degradadas_oefa")
    op.drop_index("ix_areas_degradadas_ubigeo", table_name="areas_degradadas_oefa")
    op.drop_table("areas_degradadas_oefa")

    op.drop_index(
        "ix_generacion_residuos_importacion",
        table_name="generacion_residuos_distrito_anual",
    )
    op.drop_index(
        "ix_generacion_residuos_anio",
        table_name="generacion_residuos_distrito_anual",
    )
    op.drop_index(
        "ix_generacion_residuos_ubigeo",
        table_name="generacion_residuos_distrito_anual",
    )
    op.drop_table("generacion_residuos_distrito_anual")

    op.drop_index(
        "ix_registros_rechazados_importacion",
        table_name="registros_rechazados_etl",
    )
    op.drop_table("registros_rechazados_etl")
    op.drop_table("importaciones_etl")
