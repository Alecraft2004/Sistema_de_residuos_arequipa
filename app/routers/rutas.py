
"""Endpoints para las rutas de Arequipa Recicla 2026."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .minam import cuenta_actual_minam
from ..schemas.sources_api import (
    DiccionarioRutasResponse,
    RutaResponse,
    RutasListadoResponse,
    RutasResumenResponse,
)
from ..services.sources.rutas_service import (
    RutasServiceError,
    consultar_ruta,
    consultar_rutas,
    obtener_diccionario,
    resumir_rutas,
)

router = APIRouter(
    prefix="/fuentes/rutas",
    tags=["Fuentes - Arequipa Recicla"],
)


def _manejar_error(error: RutasServiceError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("", response_model=RutasListadoResponse)
def obtener_rutas(
    dia: Annotated[str | None, Query()] = None,
    frecuencia: Annotated[str | None, Query()] = None,
    turno: Annotated[str | None, Query()] = None,
    _: dict = Depends(cuenta_actual_minam),
) -> RutasListadoResponse:
    try:
        registros = consultar_rutas(
            dia=dia,
            frecuencia=frecuencia,
            turno=turno,
        )
        return {
            "total_registros": len(registros),
            "datos": registros,
        }
    except RutasServiceError as error:
        _manejar_error(error)


@router.get("/resumen", response_model=RutasResumenResponse)
def resumen_rutas(
    _: dict = Depends(cuenta_actual_minam),
) -> RutasResumenResponse:
    try:
        return resumir_rutas()
    except RutasServiceError as error:
        _manejar_error(error)


@router.get("/diccionario", response_model=DiccionarioRutasResponse)
def diccionario_rutas(
    _: dict = Depends(cuenta_actual_minam),
) -> DiccionarioRutasResponse:
    try:
        registros = obtener_diccionario()
        return {
            "total_variables": len(registros),
            "datos": registros,
        }
    except RutasServiceError as error:
        _manejar_error(error)


@router.get("/{codigo}", response_model=RutaResponse)
def detalle_ruta(
    codigo: str,
    _: dict = Depends(cuenta_actual_minam),
) -> RutaResponse:
    try:
        ruta = consultar_ruta(codigo)

        if ruta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró la ruta solicitada.",
            )

        return ruta

    except RutasServiceError as error:
        _manejar_error(error)
