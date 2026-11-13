"""Schemas de respuesta para el API de importaciones ETL."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RechazoETLResponse(BaseModel):
    numero_fila: int
    datos_originales: dict[str, Any]
    motivo: str


class VistaPreviaETLResponse(BaseModel):
    perfil_fuente: str
    entidad: str
    nombre_archivo: str
    tipo_archivo: str
    total_filas: int
    filas_validas: int
    filas_rechazadas: int
    columnas_no_reconocidas: list[str]
    columnas_faltantes: list[str]
    muestra_transformada: list[dict[str, Any]]
    muestra_rechazos: list[RechazoETLResponse]


class ImportacionResumenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_archivo: str
    perfil_fuente: str | None
    entidad_fuente: str | None
    fecha_importacion: datetime
    estado: str
    total_filas_procesadas: int
    total_filas_validas: int
    total_filas_rechazadas: int


class ImportacionDetalleResponse(ImportacionResumenResponse):
    mensaje_error: str | None


class ImportacionesPageResponse(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[ImportacionResumenResponse]


class RechazadosPageResponse(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[RechazoETLResponse]


class EstadisticasETLResponse(BaseModel):
    total_importaciones: int
    importaciones_completadas: int
    importaciones_fallidas: int
    registros_importados_minam: int
    registros_importados_oefa: int
    registros_rechazados: int
