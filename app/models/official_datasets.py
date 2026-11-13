"""Modelos de almacenamiento para datasets oficiales MINAM y OEFA."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class GeneracionResiduoDistritoAnual(Base):
    """Generación anual agregada por distrito, año y fuente MINAM."""

    __tablename__ = "generacion_residuos_distrito_anual"
    __table_args__ = (
        Index("ix_generacion_residuos_ubigeo", "ubigeo"),
        Index("ix_generacion_residuos_anio", "anio"),
        Index("ix_generacion_residuos_importacion", "importacion_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importaciones_etl.id", ondelete="RESTRICT"), nullable=False
    )
    perfil_fuente: Mapped[str] = mapped_column(String(80), nullable=False)
    ubigeo: Mapped[str] = mapped_column(String(10), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    departamento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    distrito: Mapped[str | None] = mapped_column(String(120), nullable=True)
    poblacion_total_inei: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    poblacion_urbana_inei: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    poblacion_rural_inei: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    generacion_per_capita_domiciliaria: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    generacion_domiciliaria_urbana_t_dia: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    generacion_domiciliaria_urbana_t_anio: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    generacion_municipal_t_anio: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    generacion_municipal_t_dia: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    generacion_per_capita_municipal: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    datos_originales: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AreaDegradadaOEFA(Base):
    """Inventario geográfico de áreas degradadas de OEFA."""

    __tablename__ = "areas_degradadas_oefa"
    __table_args__ = (
        Index("ix_areas_degradadas_ubigeo", "ubigeo"),
        Index("ix_areas_degradadas_importacion", "importacion_id"),
        Index("ix_areas_degradadas_id_uf", "id_uf"),
        Index("ix_areas_degradadas_fecha_corte", "fecha_corte"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importaciones_etl.id", ondelete="RESTRICT"), nullable=False
    )
    perfil_fuente: Mapped[str] = mapped_column(String(80), nullable=False)
    ubigeo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    id_uf: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipalidad_administradora: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    denominacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zona: Mapped[str | None] = mapped_column(String(150), nullable=True)
    este: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    norte: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    perimetro: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    area_m2: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    area_ha: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    municipalidad_disponen: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    cantidad_municipalidades_disponen: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    segregacion: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    crianza_animal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    quema_rrss: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rrss_salud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rrss_industrial: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    natural_aguajal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    natural_bofedal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    natural_pantano: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    amortiguamiento_anp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    anp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(150), nullable=True)
    anio_incorporacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_corte: Mapped[date | None] = mapped_column(Date, nullable=True)
    datos_originales: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
