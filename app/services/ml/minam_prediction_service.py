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
KDD_PATH = BASE_DIR / "data" / "processed" / "minam_kdd.csv"
EVALUATION_PATH = MODEL_DIR / "evaluation" / "predictions_evaluated.csv"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
METADATA_PATH = MODEL_DIR / "model_metadata.json"

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
    source_rows: tuple[dict[str, Any], ...]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as source:
        return [dict(row) for row in csv.DictReader(source)]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_artifacts() -> ModelArtifacts:
    required = (KDD_PATH,MODEL_PATH, METADATA_PATH, METRICS_PATH, FEATURES_PATH, EVALUATION_PATH)
    missing = [str(path.name) for path in required if not path.is_file()]
    if missing:
        raise PredictionServiceError(f"Artefactos MINAM no disponibles: {', '.join(missing)}.")
    try:
        model = joblib.load(MODEL_PATH)
        metadata = _read_json(METADATA_PATH)
        metrics = _read_json(METRICS_PATH)
        historical_rows = _read_csv(FEATURES_PATH)
        evaluation_rows = _read_csv(EVALUATION_PATH)
        source_rows = _read_csv(KDD_PATH)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise PredictionServiceError("No se pudieron cargar los artefactos MINAM.") from error
    if not metadata.get("modelo_seleccionado"):
        raise PredictionServiceError(
            "Los metadatos no identifican el modelo seleccionado."
        )
    if not historical_rows:
        raise PredictionServiceError("El histórico MINAM está vacío.")
    return ModelArtifacts(
        model=model,
        metadata=metadata,
        metrics=metrics,
        historical_rows=tuple(historical_rows),
        evaluation_rows=tuple(evaluation_rows),
        source_rows=tuple(source_rows),
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
            "nombre_modelo": None,
            "tipo_modelo": None,
            "disponible": False,
            "fecha_entrenamiento": None,
            "ultimo_anio_historico": None,
            "proximo_anio_prediccion": None,
            "metodologia": None,
            "mensaje": str(error),
        }

    model_name = artifacts.metadata["modelo_seleccionado"]
    latest = max(int(row["anio"]) for row in artifacts.source_rows)

    return {
        "nombre_modelo": model_name,
        "tipo_modelo": model_name.replace("_", " "),
        "disponible": True,
        "fecha_entrenamiento": artifacts.metadata.get(
            "fecha_entrenamiento_utc"
        ),
        "ultimo_anio_historico": latest,
        "proximo_anio_prediccion": latest + 1,
        "metodologia": (
            "Baseline de persistencia."
            if model_name == "baseline_persistencia"
            else f"Modelo predictivo {model_name}."
        ),
        "mensaje": None,
    }


def _latest_by_ubigeo(
    artifacts: ModelArtifacts,
) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}

    for row in artifacts.source_rows:
        ubigeo = str(row.get("ubigeo", "")).strip().zfill(6)

        if not ubigeo or not row.get("generacion_municipal_t_anio"):
            continue

        year = int(row["anio"])

        if (
            ubigeo not in latest
            or year > int(latest[ubigeo]["anio"])
        ):
            latest[ubigeo] = {**row, "ubigeo": ubigeo}

    return list(latest.values())


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _predict_row(
    row: dict[str, Any],
    history: list[dict[str, Any]],
    artifacts: ModelArtifacts,
) -> dict[str, Any]:
    latest_year = int(row["anio"])
    target_year = latest_year + 1

    records_by_year = {
        int(item["anio"]): item
        for item in history
    }

    def generation_at(year: int) -> float | None:
        record = records_by_year.get(year)
        return (
            _number(record.get("generacion_municipal_t_anio"))
            if record else None
        )

    latest_generation = generation_at(latest_year)
    lag2 = generation_at(latest_year - 1)
    lag3 = generation_at(latest_year - 2)

    population = _number(row.get("poblacion_total_inei"))

    variation = (
        latest_generation - lag2
        if latest_generation is not None and lag2 is not None
        else None
    )

    trend = (
        (latest_generation - lag3) / 2
        if (
            latest_generation is not None
            and lag2 is not None
            and lag3 is not None
        )
        else None
    )

    features = [
        target_year,
        latest_generation,
        lag2,
        lag3,
        population,
        variation,
        trend,
    ]

    prediction = float(artifacts.model.predict([features])[0])
    model_name = artifacts.metadata["modelo_seleccionado"]

    methodology = (
        "Baseline de persistencia."
        if model_name == "baseline_persistencia"
        else f"Predicción mediante el modelo {model_name}, "
             "utilizando características históricas MINAM."
    )

    return {
        "ubigeo": str(row["ubigeo"]),
        "departamento": str(row.get("departamento", "")),
        "provincia": str(row.get("provincia", "")),
        "distrito": str(row.get("distrito", "")),
        "anio_historico": latest_year,
        "anio_objetivo": target_year,
        "generacion_real_ultimo_anio": latest_generation,
        "generacion_predicha": prediction,
        "tipo_modelo": model_name,
        "metodologia": methodology,
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

    history_by_ubigeo: dict[str, list[dict[str, Any]]] = {}

    for historical in artifacts.source_rows:
        codigo = str(historical.get("ubigeo", "")).strip().zfill(6)
        if codigo:
            history_by_ubigeo.setdefault(codigo, []).append(historical)

    result = [
        _predict_row(
            row,
            history_by_ubigeo[row["ubigeo"]],
            artifacts,
        )
        for row in rows
    ]
    if anio_objetivo is not None:
        latest_global = max(item["anio_historico"] for item in result)
        expected_year = latest_global + 1

        if anio_objetivo != expected_year:
            raise PredictionInputError(
                f"Actualmente solo se permite predecir el siguiente año disponible "
                f"({expected_year})."
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
    model_name = artifacts.metadata["modelo_seleccionado"]

    return {
        "modelo_seleccionado": model_name,
        "evaluacion_nacional_2024": (
            artifacts.metrics
            .get("metricas_prueba", {})
            .get(model_name, {})
        ),
        "evaluacion_arequipa_2024": artifacts.metrics.get(
            "metricas_prueba_arequipa", {}
        ),
        "validacion_temporal": artifacts.metrics.get(
            "validacion_temporal", {}
        ),
        "version_evaluacion": artifacts.metadata.get(
            "fecha_entrenamiento_utc"
        ),
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
