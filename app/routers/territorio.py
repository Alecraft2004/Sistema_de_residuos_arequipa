
"""Endpoints de consulta de cartografía distrital."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .minam import cuenta_actual_minam
from ..services.geo.territory_service import (
    TerritoryServiceError,
    obtener_distritos,
)
from ..services.ml.minam_historical_service import (
    HistoricalServiceError,
    listar_historico,
)


router = APIRouter(
    prefix="/territorio",
    tags=["Territorio"],
)


@router.get("/distritos")
def listar_distritos(
    departamento: Annotated[
        str | None, Query(max_length=120)
    ] = None,
    ubigeo: Annotated[
        str | None, Query(min_length=1, max_length=6)
    ] = None,
    _: dict = Depends(cuenta_actual_minam),
) -> dict:
    try:
        return obtener_distritos(
            departamento=departamento,
            ubigeo=ubigeo,
        )
    except TerritoryServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

@router.get("/distritos/generacion")
def distritos_con_generacion(
    anio: Annotated[int, Query(ge=2019, le=2100)] = 2024,
    departamento: Annotated[str | None, Query(max_length=120)] = None,
    _: dict = Depends(cuenta_actual_minam),
) -> dict:
    try:
        territorio = obtener_distritos(departamento=departamento)
        historico = listar_historico(
            anio=anio,
            departamento=departamento,
        )

        datos_por_ubigeo = {
            registro["ubigeo"]: registro
            for registro in historico
        }

        features = []

        for feature in territorio["features"]:
            propiedades = dict(feature["properties"])
            registro = datos_por_ubigeo.get(propiedades["ubigeo"])

            propiedades.update({
                "anio": anio,
                "generacion_real": (
                    registro["generacion_real"] if registro else None
                ),
                "unidad": "toneladas/año",
                "fuente": "MINAM",
                "particion_temporal": (
                    registro["particion_temporal"] if registro else None
                ),
            })

            features.append({
                **feature,
                "properties": propiedades,
            })

        return {
            "type": "FeatureCollection",
            "anio": anio,
            "departamento": departamento,
            "total": len(features),
            "features": features,
        }

    except (HistoricalServiceError, TerritoryServiceError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error