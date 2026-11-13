from __future__ import annotations

from pydantic import BaseModel


class ModeloEstadoResponse(BaseModel):
    nombre_modelo: str
    tipo_modelo: str
    disponible: bool
    fecha_entrenamiento: str | None
    ultimo_anio_historico: int | None
    proximo_anio_prediccion: int | None
    metodologia: str
    mensaje: str | None = None


class MetricasResponse(BaseModel):
    evaluacion_nacional_2024: dict
    evaluacion_arequipa_2024: dict
    validacion_temporal: dict
    version_evaluacion: str | None = None


class PrediccionMINAMResponse(BaseModel):
    ubigeo: str
    departamento: str
    provincia: str
    distrito: str
    anio_historico: int
    anio_objetivo: int
    generacion_real_ultimo_anio: float
    generacion_predicha: float
    tipo_modelo: str
    metodologia: str


class EvaluacionMINAMResponse(BaseModel):
    ubigeo: str
    departamento: str
    provincia: str
    distrito: str
    anio_objetivo: int
    generacion_real: float
    generacion_predicha: float
    error_absoluto: float
    error_porcentual: float | None
    resultado: str

