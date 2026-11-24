"""Endpoints autenticados para predicción y evaluación KDD MINAM."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..schemas.minam_api import (
    EvaluacionMINAMResponse,
    MetricasResponse,
    ModeloEstadoResponse,
    PrediccionMINAMResponse,
)
from ..services.ml.minam_prediction_service import (
    PredictionInputError,
    PredictionServiceError,
    future_prediction_by_ubigeo,
    future_predictions,
    historical_evaluation,
    metrics,
    model_state,
)
from ..services.ml.minam_historical_service import (
    HistoricalServiceError,
    listar_historico
)

router = APIRouter(prefix="/kdd/minam", tags=["KDD MINAM"])
SEGURIDAD_MINAM = HTTPBearer()


def cuenta_actual_minam(
    credenciales: HTTPAuthorizationCredentials = Depends(SEGURIDAD_MINAM),
) -> dict:
    from ..main import usuario_actual

    return usuario_actual(credenciales)


def _error_servicio(error: PredictionServiceError) -> HTTPException:
    if isinstance(error, PredictionInputError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("/modelo/estado", response_model=ModeloEstadoResponse)
def estado_modelo(_: dict = Depends(cuenta_actual_minam)) -> ModeloEstadoResponse:
    return ModeloEstadoResponse(**model_state())


@router.get("/modelo/metricas", response_model=MetricasResponse)
def metricas_modelo(_: dict = Depends(cuenta_actual_minam)) -> MetricasResponse:
    try:
        return MetricasResponse(**metrics())
    except PredictionServiceError as error:
        raise _error_servicio(error) from error


def _listar_predicciones(
    ubigeo: str | None,
    departamento: str | None,
    provincia: str | None,
    distrito: str | None,
    anio_objetivo: int | None,
) -> list[dict]:
    try:
        return future_predictions(
            ubigeo=ubigeo,
            departamento=departamento,
            provincia=provincia,
            distrito=distrito,
            anio_objetivo=anio_objetivo,
        )
    except PredictionServiceError as error:
        raise _error_servicio(error) from error


@router.get("/predicciones", response_model=list[PrediccionMINAMResponse])
def predicciones(
    ubigeo: Annotated[str | None, Query(max_length=20)] = None,
    departamento: Annotated[str | None, Query(max_length=120)] = None,
    provincia: Annotated[str | None, Query(max_length=120)] = None,
    distrito: Annotated[str | None, Query(max_length=120)] = None,
    anio_objetivo: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    _: dict = Depends(cuenta_actual_minam),
) -> list[PrediccionMINAMResponse]:
    return [
        PrediccionMINAMResponse(**row)
        for row in _listar_predicciones(
            ubigeo, departamento, provincia, distrito, anio_objetivo
        )
    ]


@router.get("/predicciones/arequipa", response_model=list[PrediccionMINAMResponse])
def predicciones_arequipa(
    anio_objetivo: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    _: dict = Depends(cuenta_actual_minam),
) -> list[PrediccionMINAMResponse]:
    return [
        PrediccionMINAMResponse(**row)
        for row in _listar_predicciones(None, "AREQUIPA", None, None, anio_objetivo)
    ]


@router.get("/predicciones/{ubigeo}", response_model=PrediccionMINAMResponse)
def prediccion_ubigeo(
    ubigeo: Annotated[str, Path(min_length=1, max_length=20)],
    _: dict = Depends(cuenta_actual_minam),
) -> PrediccionMINAMResponse:
    try:
        result = future_prediction_by_ubigeo(ubigeo)
    except PredictionServiceError as error:
        raise _error_servicio(error) from error
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UBIGEO no encontrado.")
    return PrediccionMINAMResponse(**result)


@router.get("/evaluacion/2024", response_model=list[EvaluacionMINAMResponse])
def evaluacion_2024(
    _: dict = Depends(cuenta_actual_minam),
) -> list[EvaluacionMINAMResponse]:
    try:
        return [EvaluacionMINAMResponse(**row) for row in historical_evaluation()]
    except PredictionServiceError as error:
        raise _error_servicio(error) from error


@router.get("/historico", tags=["Histórico MINAM"])
def historico_minam(
    anio: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    ubigeo: Annotated[str | None, Query(min_length=1, max_length=6)] = None,
    departamento: Annotated[str | None, Query(max_length=120)] = None,
    provincia: Annotated[str | None, Query(max_length=120)] = None,
    distrito: Annotated[str | None, Query(max_length=120)] = None,
    _: dict = Depends(cuenta_actual_minam),
) -> list[dict]:
    try:
        return listar_historico(
            anio=anio,
            ubigeo=ubigeo,
            departamento=departamento,
            provincia=provincia,
            distrito=distrito,
        )
    except HistoricalServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
