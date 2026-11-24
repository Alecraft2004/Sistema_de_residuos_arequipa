
"""Endpoints para consulta de valorización de residuos sólidos."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .minam import cuenta_actual_minam
from ..schemas.sources_api import (
    ValorizacionResponse,
    ValorizacionResumenResponse,
)
from ..services.sources.valorizacion_service import (
    ValorizacionServiceError,
    consultar_valorizacion,
    resumir_valorizacion,
)

router = APIRouter(
    prefix="/fuentes/valorizacion",
    tags=["Fuentes - Valorización"],
)


def _error_servicio(error: ValorizacionServiceError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("", response_model=ValorizacionResponse)
def obtener_valorizacion(
    tipo: Literal["organica", "inorganica"] = Query(...),
    anio: int | None = Query(default=None, ge=2019, le=2024),
    departamento: str | None = Query(default=None),
    provincia: str | None = Query(default=None),
    ubigeo: str | None = Query(default=None),
    _: dict = Depends(cuenta_actual_minam),
) -> ValorizacionResponse:
    """Consulta registros de valorización orgánica o inorgánica."""
    try:
        registros = consultar_valorizacion(
            tipo=tipo,
            anio=anio,
            departamento=departamento,
            provincia=provincia,
            ubigeo=ubigeo,
        )
        return {
            "total_registros": len(registros),
            "filtros": {
                "tipo": tipo,
                "anio": anio,
                "departamento": departamento,
                "provincia": provincia,
                "ubigeo": ubigeo,
            },
            "datos": registros,
        }
    except ValorizacionServiceError as error:
        raise _error_servicio(error) from error


@router.get("/resumen", response_model=ValorizacionResumenResponse)
def obtener_resumen_valorizacion(
    tipo: Literal["organica", "inorganica"] = Query(...),
    anio: int | None = Query(default=None, ge=2019, le=2024),
    departamento: str | None = Query(default=None),
    _: dict = Depends(cuenta_actual_minam),
) -> ValorizacionResumenResponse:
    """Obtiene indicadores resumidos de valorización."""
    try:
        return resumir_valorizacion(
            tipo=tipo,
            anio=anio,
            departamento=departamento,
        )
    except ValorizacionServiceError as error:
        raise _error_servicio(error) from error
