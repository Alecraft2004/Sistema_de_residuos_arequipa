"""Modelos de trazabilidad para importaciones ETL.

Este módulo no se importa desde ``preparar_base_datos`` deliberadamente:
el proyecto todavía no tiene migraciones versionadas y no debe crear tablas
nuevas automáticamente al iniciar la API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ImportacionETL(Base):
    """Auditoría de un archivo recibido por el proceso ETL."""

    __tablename__ = "importaciones_etl"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente', 'procesando', 'completado', 'fallido')",
            name="ck_importaciones_etl_estado",
        ),
        UniqueConstraint(
            "hash_archivo",
            "perfil_fuente",
            name="uq_importaciones_etl_hash_perfil",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(String(20), nullable=False)
    perfil_fuente: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entidad_fuente: Mapped[str | None] = mapped_column(String(150), nullable=True)
    hash_archivo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fecha_importacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    total_filas_procesadas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_filas_validas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_filas_rechazadas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente", server_default="pendiente"
    )
    mensaje_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class RegistroRechazadoETL(Base):
    """Fila rechazada conservando sus datos originales y el motivo."""

    __tablename__ = "registros_rechazados_etl"
    __table_args__ = (
        Index("ix_registros_rechazados_importacion", "importacion_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    importacion_id: Mapped[int] = mapped_column(
        ForeignKey("importaciones_etl.id", ondelete="CASCADE"), nullable=False
    )
    numero_fila: Mapped[int] = mapped_column(Integer, nullable=False)
    datos_originales: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    motivo_rechazo: Mapped[str] = mapped_column(String(1000), nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
