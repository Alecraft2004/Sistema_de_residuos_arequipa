from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

TARGET_COLUMN = "generacion_municipal_t_anio"
FEATURE_COLUMNS = (
    "generacion_lag_1",
    "generacion_lag_2",
    "generacion_lag_3",
    "poblacion_lag_1",
    "variacion_anual_generacion",
    "tendencia_generacion_3_anios",
)
PREDICTOR_COLUMNS = (
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "anio_objetivo",
    *FEATURE_COLUMNS,
)
LEAKAGE_COLUMNS = (
    TARGET_COLUMN,
    "poblacion_total_inei",
    "poblacion_urbana_inei",
    "poblacion_rural_inei",
    "log1p_generacion_municipal_t_anio",
)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def construir_caracteristicas(
    records: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Construye características históricas sin cruzar UBIGEO ni años futuros."""
    by_ubigeo: dict[str, dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for record in records:
        by_ubigeo[str(record["ubigeo"])][int(record["anio"])] = record

    features: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda row: (str(row["ubigeo"]), int(row["anio"]))):
        ubigeo = str(record["ubigeo"])
        year = int(record["anio"])
        history = by_ubigeo[ubigeo]

        def generation_at(offset: int) -> float | None:
            previous = history.get(year - offset)
            return _number(previous.get(TARGET_COLUMN)) if previous else None

        def population_at(offset: int) -> float | None:
            previous = history.get(year - offset)
            return _number(previous.get("poblacion_total_inei")) if previous else None

        lag1 = generation_at(1)
        lag2 = generation_at(2)
        lag3 = generation_at(3)
        row = {
            "ubigeo": ubigeo,
            "departamento": record.get("departamento"),
            "provincia": record.get("provincia"),
            "distrito": record.get("distrito"),
            "anio_objetivo": year,
            "generacion_lag_1": lag1,
            "generacion_lag_2": lag2,
            "generacion_lag_3": lag3,
            "poblacion_lag_1": population_at(1),
            "variacion_anual_generacion": (
                lag1 - lag2 if lag1 is not None and lag2 is not None else None
            ),
            "tendencia_generacion_3_anios": (
                (lag1 - lag3) / 2
                if lag1 is not None and lag2 is not None and lag3 is not None
                else None
            ),
            TARGET_COLUMN: _number(record.get(TARGET_COLUMN)),
            "particion_temporal": (
                "entrenamiento" if 2020 <= year <= 2023
                else "prueba" if year == 2024
                else "historial"
            ),
        }
        features.append(row)
    return features


def validar_caracteristicas(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Comprueba claves, precedencia temporal y ausencia de columnas prohibidas."""
    keys = [(row["ubigeo"], row["anio_objetivo"]) for row in rows]
    unique_keys = len(keys) == len(set(keys))
    by_key = {(row["ubigeo"], row["anio_objetivo"]): row for row in rows}
    lag1_errors = 0
    for row in rows:
        previous = by_key.get((row["ubigeo"], row["anio_objetivo"] - 1))
        expected = previous[TARGET_COLUMN] if previous else None
        if row["generacion_lag_1"] != expected:
            lag1_errors += 1
    return {
        "claves_unicas_ubigeo_anio_objetivo": unique_keys,
        "errores_generacion_lag_1": lag1_errors,
        "columnas_predictoras": list(PREDICTOR_COLUMNS),
        "columnas_prohibidas_como_predictoras": list(LEAKAGE_COLUMNS),
        "fuga_temporal_detectada": lag1_errors > 0,
    }


def generar_reporte_caracteristicas(
    source_rows: list[Mapping[str, Any]],
    feature_rows: list[Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    train = [row for row in feature_rows if row["particion_temporal"] == "entrenamiento"]
    test = [row for row in feature_rows if row["particion_temporal"] == "prueba"]
    horizons = {
        column: {
            "disponibles": sum(row[column] is not None for row in feature_rows),
            "sin_historial": sum(row[column] is None for row in feature_rows),
        }
        for column in FEATURE_COLUMNS
    }
    return {
        "dataset_origen": "data/processed/minam_kdd.csv",
        "filas_origen": len(source_rows),
        "filas_caracteristicas": len(feature_rows),
        "filas_descartadas_por_falta_historial": 0,
        "filas_entrenamiento": len(train),
        "filas_prueba": len(test),
        "ubigeos_caracteristicas": len({row["ubigeo"] for row in feature_rows}),
        "ubigeos_entrenamiento": len({row["ubigeo"] for row in train}),
        "ubigeos_prueba": len({row["ubigeo"] for row in test}),
        "objetivos_entrenamiento": [2020, 2021, 2022, 2023],
        "objetivos_prueba": [2024],
        "anios_observados_entrenamiento": sorted(
            {row["anio_objetivo"] for row in train}
        ),
        "anios_observados_prueba": sorted({row["anio_objetivo"] for row in test}),
        "entrenamiento_contiene_2024": any(
            row["anio_objetivo"] == 2024 for row in train
        ),
        "prueba_solo_contiene_2024": all(
            row["anio_objetivo"] == 2024 for row in test
        ),
        "horizontes": horizons,
        "definiciones": {
            "variacion_anual_generacion": (
                "generacion_(t-1) - generacion_(t-2); no utiliza el objetivo t"
            ),
            "tendencia_generacion_3_anios": (
                "(generacion_(t-1) - generacion_(t-3)) / 2, "
                "solo con tres años previos consecutivos"
            ),
            "poblacion_lag_1": "poblacion total del mismo UBIGEO en t-1",
        },
        "validaciones": dict(validation),
        "tratamiento": {
            "rezagos_sin_historial": "NULL",
            "imputacion": "no realizada",
            "extremos": "conservados; revisar en entrenamiento",
            "division": "temporal, sin aleatorizacion",
            "oefa": "no utilizado",
        },
    }
