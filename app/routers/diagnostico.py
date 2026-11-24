
"""Endpoints del diagnóstico territorial."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routers.minam import cuenta_actual_minam
from app.services.geo.diagnostico_service import (
    DiagnosticoServiceError,
    obtener_diagnostico,
    obtener_resumen_diagnostico,
    priorizar_distritos,
    obtener_mapa_diagnostico,
    generar_plan_atencion,
    obtener_dashboard_diagnostico,
)

router = APIRouter(
    prefix="/diagnostico",
    tags=["Diagnóstico territorial"],
)


@router.get("/")
def listar_diagnosticos(
    anio: int = Query(default=2024, ge=2019, le=2024),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        resultados = obtener_diagnostico(anio)
        return {
            "total": len(resultados),
            "anio": anio,
            "resultados": resultados,
        }
    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.get("/resumen")
def resumen_diagnostico(
    anio: int = Query(default=2024, ge=2019, le=2024),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        return obtener_resumen_diagnostico(anio)
    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.get("/priorizacion")
def listar_priorizacion(
    anio: int = Query(default=2024, ge=2019, le=2024),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        resultados = priorizar_distritos(anio)
        return {
            "total": len(resultados),
            "anio": anio,
            "metodologia": (
                "Clasificación orientativa según percentil de generación "
                "proyectada y presencia de áreas degradadas registradas "
                "por OEFA. No representa una predicción de acumulación."
            ),
            "resultados": resultados,
        }
    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

@router.get("/mapa")
def mapa_diagnostico(
    anio: int = Query(default=2024, ge=2019, le=2024),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        return obtener_mapa_diagnostico(anio)
    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

@router.get("/plan-atencion")
def plan_atencion(
    anio: int = Query(default=2024, ge=2019, le=2024),
    limite: int = Query(default=20, ge=1, le=109),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        return generar_plan_atencion(anio, limite)
    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

@router.get("/dashboard")
def dashboard_diagnostico(
    anio: int = Query(default=2024, ge=2019, le=2024),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        return obtener_dashboard_diagnostico(anio)
    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

@router.get("/{ubigeo}")
def detalle_diagnostico(
    ubigeo: str,
    anio: int = Query(default=2024, ge=2019, le=2024),
    _: dict = Depends(cuenta_actual_minam),
):
    try:
        resultados = obtener_diagnostico(anio, ubigeo)

        if not resultados:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró el distrito solicitado.",
            )

        return resultados[0]

    except DiagnosticoServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

