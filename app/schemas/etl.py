"""Schemas configurables para el pipeline ETL."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConfiguracionColumnasETL(BaseModel):
    """Mapeo y reglas declarativas por fuente de datos.

    Los nombres concretos de columnas del negocio deben confirmarse antes de
    configurar esta estructura para una carga real.
    """

    model_config = ConfigDict(extra="forbid")

    perfil_id: str | None = None
    fuente: str | None = None
    entidad: str | None = None
    mapeo_columnas: dict[str, str] = Field(default_factory=dict)
    encabezados_originales: tuple[str, ...] = ()
    columnas_obligatorias: set[str] = Field(default_factory=set)
    columnas_no_negativas: set[str] = Field(default_factory=set)
    columnas_fecha: set[str] = Field(default_factory=set)
    tipos: dict[str, str] = Field(default_factory=dict)
    claves_duplicado: list[str] = Field(default_factory=list)
    categorias: dict[str, dict[str, str]] = Field(default_factory=dict)
    conversiones_unidad: dict[str, dict[str, float]] = Field(default_factory=dict)
    campos_geograficos: set[str] = Field(default_factory=set)
    campos_temporales: set[str] = Field(default_factory=set)
    unidades: dict[str, str] = Field(default_factory=dict)
    anio_desde: int | None = None
    anio_hasta: int | None = None
    permitir_anios_futuros: bool = True
