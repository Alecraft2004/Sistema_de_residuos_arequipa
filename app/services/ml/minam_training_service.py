from __future__ import annotations

import csv
import math
import platform
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TARGET = "generacion_municipal_t_anio"
FEATURE_COLUMNS = (
    "anio_objetivo",
    "generacion_lag_1",
    "generacion_lag_2",
    "generacion_lag_3",
    "poblacion_lag_1",
    "variacion_anual_generacion",
    "tendencia_generacion_3_anios",
)
FORBIDDEN_COLUMNS = {
    TARGET,
    "log1p_generacion_municipal_t_anio",
    "particion_temporal",
    "poblacion_total_inei",
    "poblacion_urbana_inei",
    "poblacion_rural_inei",
}
RANDOM_STATE = 42
MODEL_NAMES = ("linear_regression", "random_forest", "hist_gradient_boosting")


class PersistenceBaseline:
    """Predictor reproducible que usa exclusivamente la generación del año anterior."""

    def fit(self, x: np.ndarray, y: np.ndarray) -> "PersistenceBaseline":
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        predictions = np.asarray(x, dtype=float)[:, 1]
        if np.isnan(predictions).any():
            raise ValueError("El baseline requiere generacion_lag_1 disponible.")
        return predictions


def leer_csv_minam(path: Path) -> list[dict[str, Any]]:
    numeric = {"anio_objetivo", *FEATURE_COLUMNS[1:], TARGET}
    with path.open(encoding="utf-8", newline="") as source:
        rows: list[dict[str, Any]] = []
        for raw in csv.DictReader(source):
            row: dict[str, Any] = dict(raw)
            for column in numeric:
                if row[column] == "":
                    row[column] = None
                elif column == "anio_objetivo":
                    row[column] = int(row[column])
                else:
                    row[column] = float(row[column])
            rows.append(row)
    return rows


def validar_contrato_datos(
    train_rows: list[Mapping[str, Any]],
    test_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    missing_columns = [
        column
        for column in (*FEATURE_COLUMNS, TARGET)
        if any(column not in row for row in (*train_rows, *test_rows))
    ]
    train_years = {int(row["anio_objetivo"]) for row in train_rows}
    test_years = {int(row["anio_objetivo"]) for row in test_rows}
    leakage = sorted(set(FEATURE_COLUMNS) & FORBIDDEN_COLUMNS)
    non_numeric_target = any(
        not isinstance(row[TARGET], (int, float)) or not math.isfinite(float(row[TARGET]))
        for row in (*train_rows, *test_rows)
    )
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {missing_columns}")
    if train_years != {2020, 2021, 2022, 2023}:
        raise ValueError(f"Años de entrenamiento inesperados: {sorted(train_years)}")
    if test_years != {2024}:
        raise ValueError(f"El conjunto de prueba debe contener solo 2024: {sorted(test_years)}")
    if leakage:
        raise ValueError(f"Columnas con fuga en predictores: {leakage}")
    if non_numeric_target:
        raise ValueError("La variable objetivo contiene valores no numéricos.")
    return {
        "columnas_predictoras": list(FEATURE_COLUMNS),
        "variable_objetivo": TARGET,
        "anios_entrenamiento": sorted(train_years),
        "anios_prueba": sorted(test_years),
        "fuga_detectada": False,
    }


def _matriz(rows: Iterable[Mapping[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    data = list(rows)
    x = np.array(
        [[row[column] for column in FEATURE_COLUMNS] for row in data],
        dtype=float,
    )
    y = np.array([row[TARGET] for row in data], dtype=float)
    return x, y


def crear_modelos() -> dict[str, Pipeline]:
    return {
        "linear_regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        min_samples_leaf=2,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        learning_rate=0.05,
                        max_iter=300,
                        max_leaf_nodes=31,
                        l2_regularization=1.0,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def calcular_metricas(
    reales: Iterable[float],
    predichos: Iterable[float],
) -> dict[str, float | int | None]:
    y_true = np.asarray(list(reales), dtype=float)
    y_pred = np.asarray(list(predichos), dtype=float)
    if len(y_true) == 0:
        return {"mae": None, "rmse": None, "r2": None, "observaciones": 0}
    r2 = (
        float(r2_score(y_true, y_pred))
        if len(y_true) >= 2 and np.ptp(y_true) > 0
        else None
    )
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": r2,
        "observaciones": int(len(y_true)),
    }


def _metricas_por_grupo(
    rows: list[Mapping[str, Any]],
    predictions: np.ndarray,
    key: str,
) -> dict[str, dict[str, float | int | None]]:
    groups: dict[str, tuple[list[float], list[float]]] = {}
    for row, prediction in zip(rows, predictions):
        group = str(row[key])
        actuals, predicted = groups.setdefault(group, ([], []))
        actuals.append(float(row[TARGET]))
        predicted.append(float(prediction))
    return {
        group: calcular_metricas(actuals, predicted)
        for group, (actuals, predicted) in sorted(groups.items())
    }


def _resumen_residuos(
    rows: list[Mapping[str, Any]],
    predictions: np.ndarray,
) -> dict[str, float | int]:
    residuals = np.asarray(
        [
            float(prediction) - float(row[TARGET])
            for row, prediction in zip(rows, predictions)
        ],
        dtype=float,
    )
    return {
        "observaciones": int(len(residuals)),
        "media": float(np.mean(residuals)),
        "mediana": float(np.median(residuals)),
        "desviacion_estandar": float(np.std(residuals)),
        "minimo": float(np.min(residuals)),
        "maximo": float(np.max(residuals)),
        "p95_absoluto": float(np.percentile(np.abs(residuals), 95)),
    }


def _evaluar_modelo(
    model: Pipeline,
    rows: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], np.ndarray]:
    x, y = _matriz(rows)
    predictions = model.predict(x)
    return calcular_metricas(y, predictions), predictions


def _evaluar_baseline(rows: list[Mapping[str, Any]]) -> tuple[dict[str, Any], np.ndarray]:
    available = [row for row in rows if row["generacion_lag_1"] is not None]
    actuals = [float(row[TARGET]) for row in available]
    predictions = np.array([float(row["generacion_lag_1"]) for row in available])
    return calcular_metricas(actuals, predictions), predictions


def validacion_temporal(
    train_rows: list[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {
        "baseline_persistencia": [],
        **{name: [] for name in MODEL_NAMES},
    }
    for validation_year in (2022, 2023):
        fitting_rows = [
            row for row in train_rows if 2020 <= row["anio_objetivo"] < validation_year
        ]
        validation_rows = [
            row for row in train_rows if row["anio_objetivo"] == validation_year
        ]
        baseline_metrics, _ = _evaluar_baseline(validation_rows)
        results["baseline_persistencia"].append(
            {"anio_validacion": validation_year, **baseline_metrics}
        )
        for name, model in crear_modelos().items():
            x_train, y_train = _matriz(fitting_rows)
            model.fit(x_train, y_train)
            metrics, _ = _evaluar_modelo(model, validation_rows)
            results[name].append(
                {"anio_validacion": validation_year, **metrics}
            )
    return results


def _promedios_validacion(
    results: Mapping[str, list[Mapping[str, Any]]],
) -> dict[str, dict[str, float | None]]:
    summary: dict[str, dict[str, float | None]] = {}
    for name, folds in results.items():
        maes = [float(fold["mae"]) for fold in folds if fold["mae"] is not None]
        rmses = [float(fold["rmse"]) for fold in folds if fold["rmse"] is not None]
        summary[name] = {
            "mae_promedio": float(np.mean(maes)) if maes else None,
            "rmse_promedio": float(np.mean(rmses)) if rmses else None,
        }
    return summary


def _seleccionar_modelo(summary: Mapping[str, Mapping[str, Any]]) -> str:
    candidates = [
        (name, values)
        for name, values in summary.items()
        if values["mae_promedio"] is not None
    ]
    return min(
        candidates,
        key=lambda item: (
            float(item[1]["mae_promedio"]),
            float(item[1]["rmse_promedio"]),
        ),
    )[0]


def _importancia(model: Any) -> list[dict[str, Any]]:
    if not isinstance(model, Pipeline):
        return []
    estimator = model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
        method = "feature_importances_"
    elif hasattr(estimator, "coef_"):
        values = np.abs(estimator.coef_)
        method = "absolute_coefficient"
    else:
        return []
    return [
        {
            "variable": feature,
            "importancia": float(value),
            "metodo": method,
        }
        for feature, value in zip(FEATURE_COLUMNS, values)
    ]


def _importancias_arboles(models: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_name in ("random_forest", "hist_gradient_boosting"):
        for row in _importancia(models[model_name]):
            rows.append({"modelo": model_name, **row})
    return rows


def entrenar_y_evaluar(
    train_rows: list[Mapping[str, Any]],
    test_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    contrato = validar_contrato_datos(train_rows, test_rows)
    validation = validacion_temporal(train_rows)
    validation_summary = _promedios_validacion(validation)
    selected_name = _seleccionar_modelo(validation_summary)

    final_models: dict[str, Any] = {
        "baseline_persistencia": PersistenceBaseline(),
        **crear_modelos(),
    }
    final_metrics: dict[str, Any] = {}
    final_predictions: dict[str, np.ndarray] = {}
    x_train, y_train = _matriz(train_rows)
    for name, model in final_models.items():
        if name == "baseline_persistencia":
            metrics, predictions = _evaluar_baseline(test_rows)
        else:
            model.fit(x_train, y_train)
            metrics, predictions = _evaluar_modelo(model, test_rows)
        final_metrics[name] = metrics
        final_predictions[name] = predictions

    selected_model = final_models[selected_name]
    selected_predictions = final_predictions[selected_name]
    prediction_rows = []
    for row, prediction in zip(test_rows, selected_predictions):
        actual = float(row[TARGET])
        error = abs(actual - float(prediction))
        prediction_rows.append(
            {
                "ubigeo": row["ubigeo"],
                "departamento": row["departamento"],
                "provincia": row["provincia"],
                "distrito": row["distrito"],
                "anio_objetivo": row["anio_objetivo"],
                "generacion_real": actual,
                "generacion_predicha": float(prediction),
                "error_absoluto": error,
                "error_porcentual": error / abs(actual) * 100 if actual != 0 else None,
            }
        )
    return {
        "contrato": contrato,
        "validacion_temporal": validation,
        "validacion_resumen": validation_summary,
        "modelo_seleccionado": selected_name,
        "metricas_prueba": final_metrics,
        "predicciones": prediction_rows,
        "importancia": _importancias_arboles(final_models),
        "metricas_prueba_arequipa": _metricas_por_grupo(
            test_rows,
            selected_predictions,
            "departamento",
        ).get("AREQUIPA", calcular_metricas([], [])),
        "resumen_residuos_prueba": _resumen_residuos(
            test_rows,
            selected_predictions,
        ),
        "metricas_prueba_departamento": _metricas_por_grupo(
            test_rows,
            selected_predictions,
            "departamento",
        ),
        "metricas_prueba_distrito": _metricas_por_grupo(
            test_rows,
            selected_predictions,
            "distrito",
        ),
        "filas_entrenamiento": len(train_rows),
        "filas_prueba": len(test_rows),
        "modelo": selected_model,
    }


def crear_metadata(resultado: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "modelo_seleccionado": resultado["modelo_seleccionado"],
        "variable_objetivo": TARGET,
        "variables_predictoras": list(FEATURE_COLUMNS),
        "periodo_entrenamiento": [2020, 2023],
        "periodo_prueba": [2024],
        "filas_entrenamiento": resultado["filas_entrenamiento"],
        "filas_prueba": resultado["filas_prueba"],
        "random_state": RANDOM_STATE,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "fecha_entrenamiento_utc": datetime.now(timezone.utc).isoformat(),
        "imputacion": "SimpleImputer(strategy='median', keep_empty_features=True) dentro de cada Pipeline",
        "validacion": "origen expansivo: 2020-2021->2022 y 2020-2022->2023",
        "oeFA_utilizado": False,
    }
