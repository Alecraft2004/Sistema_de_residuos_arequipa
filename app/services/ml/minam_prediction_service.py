from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

BASE_DIR = Path(__file__).resolve().parents[3]
MODEL_DIR = BASE_DIR / "data" / "models" / "minam"
FEATURES_PATH = BASE_DIR / "data" / "processed" / "minam_features.csv"
EVALUATION_PATH = MODEL_DIR / "evaluation" / "predictions_evaluated.csv"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
METADATA_PATH = MODEL_DIR / "model_metadata.json"

MODEL_NAME = "baseline_persistencia"
METHODOLOGY = (
    "Baseline de persistencia: la predicción del siguiente año utiliza "
    "la generación municipal real del último año disponible para el mismo UBIGEO."
)


class PredictionServiceError(Exception):
    """Error controlado al consultar los artefactos de predicción."""


class PredictionInputError(PredictionServiceError):
    """Parámetro de predicción incompatible con el histórico disponible."""


@dataclass(frozen=True)
class ModelArtifacts:
    model: Any
    metadata: dict[str, Any]
    metrics: dict[str, Any]
    historical_rows: tuple[dict[str, Any], ...]
    evaluation_rows: tuple[dict[str, Any], ...]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as source:
        return [dict(row) for row in csv.DictReader(source)]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_artifacts() -> ModelArtifacts:
    required = (MODEL_PATH, METADATA_PATH, METRICS_PATH, FEATURES_PATH, EVALUATION_PATH)
    missing = [str(path.name) for path in required if not path.is_file()]
    if missing:
        raise PredictionServiceError(f"Artefactos MINAM no disponibles: {', '.join(missing)}.")
    try:
        model = joblib.load(MODEL_PATH)
        metadata = _read_json(METADATA_PATH)
        metrics = _read_json(METRICS_PATH)
        historical_rows = _read_csv(FEATURES_PATH)
        evaluation_rows = _read_csv(EVALUATION_PATH)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise PredictionServiceError("No se pudieron cargar los artefactos MINAM.") from error
    if metadata.get("modelo_seleccionado") != MODEL_NAME:
        raise PredictionServiceError("El artefacto disponible no corresponde al baseline esperado.")
    if not historical_rows:
        raise PredictionServiceError("El histórico MINAM está vacío.")
    return ModelArtifacts(
        model=model,
        metadata=metadata,
        metrics=metrics,
        historical_rows=tuple(historical_rows),
        evaluation_rows=tuple(evaluation_rows),
    )


@lru_cache(maxsize=1)
def get_artifacts() -> ModelArtifacts:
    """Carga los artefactos una sola vez por proceso."""
    return _load_artifacts()


def clear_artifact_cache() -> None:
    get_artifacts.cache_clear()


def model_state() -> dict[str, Any]:
    try:
        artifacts = get_artifacts()
    except PredictionServiceError as error:
        return {
            "nombre_modelo": MODEL_NAME,
            "tipo_modelo": "baseline de persistencia",
            "disponible": False,
            "fecha_entrenamiento": None,
            "ultimo_anio_historico": None,
            "proximo_anio_prediccion": None,
            "metodologia": METHODOLOGY,
            "mensaje": str(error),
        }
    latest = max(int(row["anio_objetivo"]) for row in artifacts.historical_rows)
    return {
        "nombre_modelo": MODEL_NAME,
        "tipo_modelo": "baseline de persistencia",
        "disponible": True,
        "fecha_entrenamiento": artifacts.metadata.get("fecha_entrenamiento_utc"),
        "ultimo_anio_historico": latest,
        "proximo_anio_prediccion": latest + 1,
        "metodologia": METHODOLOGY,
        "mensaje": None,
    }


def _latest_by_ubigeo(artifacts: ModelArtifacts) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in artifacts.historical_rows:
        ubigeo = str(row.get("ubigeo", "")).strip()
        if not ubigeo or row.get("generacion_municipal_t_anio", "") == "":
            continue
        if ubigeo not in latest or int(row["anio_objetivo"]) > int(latest[ubigeo]["anio_objetivo"]):
            latest[ubigeo] = row
    return list(latest.values())


def _predict_row(row: dict[str, Any]) -> dict[str, Any]:
    current = float(row["generacion_municipal_t_anio"])
    target_year = int(row["anio_objetivo"]) + 1
    values = [[target_year, current, None, None, None, None, None]]
    prediction = float(get_artifacts().model.predict(values)[0])
    return {
        "ubigeo": str(row["ubigeo"]),
        "departamento": str(row.get("departamento", "")),
        "provincia": str(row.get("provincia", "")),
        "distrito": str(row.get("distrito", "")),
        "anio_historico": int(row["anio_objetivo"]),
        "anio_objetivo": target_year,
        "generacion_real_ultimo_anio": current,
        "generacion_predicha": prediction,
        "tipo_modelo": "baseline_persistencia",
        "metodologia": METHODOLOGY,
    }


def future_predictions(
    *,
    ubigeo: str | None = None,
    departamento: str | None = None,
    provincia: str | None = None,
    distrito: str | None = None,
    anio_objetivo: int | None = None,
) -> list[dict[str, Any]]:
    artifacts = get_artifacts()
    rows = _latest_by_ubigeo(artifacts)
    result = [_predict_row(row) for row in rows]
    if anio_objetivo is not None:
        latest_global = max(item["anio_historico"] for item in result)
        if anio_objetivo <= latest_global:
            raise PredictionInputError(
                f"El año objetivo debe ser posterior al último año histórico ({latest_global})."
            )
    filters = {
        "ubigeo": ubigeo,
        "departamento": departamento,
        "provincia": provincia,
        "distrito": distrito,
        "anio_objetivo": anio_objetivo,
    }
    for field, value in filters.items():
        if value is not None:
            result = [
                item for item in result
                if str(item[field]).casefold() == str(value).casefold()
            ]
    return result


def future_prediction_by_ubigeo(ubigeo: str) -> dict[str, Any] | None:
    result = future_predictions(ubigeo=ubigeo)
    return result[0] if result else None


def metrics() -> dict[str, Any]:
    artifacts = get_artifacts()
    return {
        "evaluacion_nacional_2024": artifacts.metrics.get("metricas_prueba", {}).get(MODEL_NAME, {}),
        "evaluacion_arequipa_2024": artifacts.metrics.get("metricas_prueba_arequipa", {}),
        "validacion_temporal": artifacts.metrics.get("validacion_temporal", {}),
        "version_evaluacion": artifacts.metadata.get("fecha_entrenamiento_utc"),
    }


def historical_evaluation() -> list[dict[str, Any]]:
    artifacts = get_artifacts()
    result = []
    for row in artifacts.evaluation_rows:
        result.append(
            {
                "ubigeo": str(row["ubigeo"]),
                "departamento": str(row["departamento"]),
                "provincia": str(row["provincia"]),
                "distrito": str(row["distrito"]),
                "anio_objetivo": int(row["anio_objetivo"]),
                "generacion_real": float(row["generacion_real"]),
                "generacion_predicha": float(row["generacion_predicha"]),
                "error_absoluto": float(row["error_absoluto"]),
                "error_porcentual": (
                    float(row["error_porcentual"])
                    if row.get("error_porcentual", "") != ""
                    else None
                ),
                "resultado": "evaluacion_historica_2024",
            }
        )
    return result
