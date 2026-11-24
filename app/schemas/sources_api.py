"""Schemas de respuesta para las fuentes externas del sistema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# OEFA
# ============================================================

class OefaListadoResponse(BaseModel):
    """Respuesta paginada del inventario de áreas degradadas OEFA."""

    total_registros: int = Field(description="Total de registros encontrados antes de paginar.")
    limite: int = Field(description="Cantidad máxima de registros devueltos.")
    desplazamiento: int = Field(description="Cantidad de registros omitidos.")
    datos: list[dict[str, Any]] = Field(
        description="Registros originales normalizados del inventario OEFA."
    )


class OefaDetalleResponse(BaseModel):
    """Respuesta de consulta por identificador OEFA."""

    total_registros: int
    datos: list[dict[str, Any]]


class OefaResumenResponse(BaseModel):
    """Indicadores generales del inventario OEFA."""

    total_registros: int
    por_categoria: dict[str, int]
    por_departamento: dict[str, int]
    por_anio_incorporacion: dict[str, int]
    con_ubigeo: int
    con_coordenadas: int
    con_area_ha: int
    fecha_corte: list[str]
    fuente: str
    nota: str


# ============================================================
# AREQUIPA RECICLA
# ============================================================

class RutaResponse(BaseModel):
    """Registro de una ruta de recolección selectiva."""

    numero: int | float | str | None
    codigo: str
    descripcion: str | None
    dia: str | None
    frecuencia: str | None
    turno: str | None
    hora: str | None
    fuente: str


class RutasListadoResponse(BaseModel):
    """Listado de rutas de Arequipa Recicla."""

    total_registros: int
    datos: list[RutaResponse]


class RutaDetalleResponse(RutaResponse):
    """Detalle de una ruta específica."""


class RutasResumenResponse(BaseModel):
    """Indicadores generales de las rutas."""

    total_rutas: int
    por_dia: dict[str, int]
    por_frecuencia: dict[str, int]
    por_turno: dict[str, int]
    rutas_con_datos_incompletos: int
    fuente: str


class DiccionarioRutaResponse(BaseModel):
    """Descripción de una variable del diccionario de rutas."""

    variable: str
    descripcion: str
    tipo_dato: str | int | float | None
    tamano: str | int | float | None
    informacion_adicional: str | None


class DiccionarioRutasResponse(BaseModel):
    """Diccionario de variables del programa Arequipa Recicla."""

    total_variables: int
    datos: list[DiccionarioRutaResponse]


# ============================================================
# VALORIZACIÓN
# ============================================================

class ValorizacionRegistroResponse(BaseModel):
    """Registro distrital de valorización de residuos sólidos."""

    ubigeo: str
    departamento: str
    provincia: str
    distrito: str
    anio: int
    valor: float
    tipo: str
    fuente: str


class FiltrosValorizacionResponse(BaseModel):
    """Filtros aplicados a la consulta de valorización."""

    tipo: str
    anio: int | None
    departamento: str | None
    provincia: str | None
    ubigeo: str | None


class ValorizacionResponse(BaseModel):
    """Listado de registros de valorización."""

    total_registros: int
    filtros: FiltrosValorizacionResponse
    datos: list[ValorizacionRegistroResponse]


class ValorizacionResumenResponse(BaseModel):
    """Indicadores agregados de valorización."""

    tipo: str
    anio: int | None
    departamento: str | None
    total_registros: int
    total_valorizado: float
    promedio: float
    distritos: int
    fuente: str | None
    unidad: str | None = Field(
        default=None,
        description="Unidad de medida. Permanece sin especificar hasta confirmar los metadatos."
    )
    nota: str
