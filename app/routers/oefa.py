
"""Endpoints de consulta del inventario OEFA."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .minam import cuenta_actual_minam
from ..schemas.sources_api import (
    OefaDetalleResponse,
    OefaListadoResponse,
    OefaResumenResponse,
)
from ..services.sources.oefa_service import (
    OefaServiceError,
    consultar_areas_oefa,
    consultar_area_oefa,
    resumir_areas_oefa,
)

router = APIRouter(
    prefix="/fuentes/oefa",
    tags=["Fuentes - OEFA"],
)


def _manejar_error(error: OefaServiceError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("", response_model=OefaListadoResponse)
def obtener_areas_oefa(
    departamento: Annotated[str | None, Query()] = None,
    provincia: Annotated[str | None, Query()] = None,
    distrito: Annotated[str | None, Query()] = None,
    categoria: Annotated[str | None, Query()] = None,
    anio_incorporacion: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
    desplazamiento: Annotated[int, Query(ge=0)] = 0,
    _: dict = Depends(cuenta_actual_minam),
) -> OefaListadoResponse:
    try:
        registros = consultar_areas_oefa(
            departamento=departamento,
            provincia=provincia,
            distrito=distrito,
            categoria=categoria,
            anio_incorporacion=anio_incorporacion,
        )

        total = len(registros)
        datos = registros[desplazamiento:desplazamiento + limite]

        return {
            "total_registros": total,
            "limite": limite,
            "desplazamiento": desplazamiento,
            "datos": datos,
        }

    except OefaServiceError as error:
        _manejar_error(error)


@router.get("/resumen", response_model=OefaResumenResponse)
def resumen_oefa(
    _: dict = Depends(cuenta_actual_minam),
) -> OefaResumenResponse:
    try:
        return resumir_areas_oefa()
    except OefaServiceError as error:
        _manejar_error(error)


@router.get("/{id_uf}", response_model=OefaDetalleResponse)
def detalle_area_oefa(
    id_uf: str,
    _: dict = Depends(cuenta_actual_minam),
) -> OefaDetalleResponse:
    try:
        registros = consultar_area_oefa(id_uf)

        if not registros:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró el identificador OEFA solicitado.",
            )

        return {
            "total_registros": len(registros),
            "datos": registros,
        }

    except OefaServiceError as error:
        _manejar_error(error)
