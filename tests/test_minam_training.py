from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import joblib

from app.services.ml.minam_training_service import (
    FEATURE_COLUMNS,
    TARGET,
    calcular_metricas,
    crear_modelos,
    entrenar_y_evaluar,
)


def _row(year: int, target: float, lag1: float | None) -> dict:
    return {
        "ubigeo": "010101",
        "departamento": "AREQUIPA",
        "provincia": "AREQUIPA",
        "distrito": "CERCADO",
        "anio_objetivo": year,
        "generacion_lag_1": lag1,
        "generacion_lag_2": lag1,
        "generacion_lag_3": lag1,
        "poblacion_lag_1": 100.0,
        "variacion_anual_generacion": 1.0,
        "tendencia_generacion_3_anios": 1.0,
        TARGET: target,
    }


class MINAMTrainingTestCase(unittest.TestCase):
    def test_metricas_regresion(self) -> None:
        metrics = calcular_metricas([1, 2, 3], [1, 3, 2])
        self.assertEqual(metrics["observaciones"], 3)
        self.assertAlmostEqual(metrics["mae"], 2 / 3)

    def test_modelos_tienen_imputacion_en_pipeline(self) -> None:
        for model in crear_modelos().values():
            self.assertIn("imputer", model.named_steps)

    def test_entrenamiento_separa_2024_y_no_hay_fuga(self) -> None:
        train = [_row(year, 10 + year - 2020, 9 + year - 2020) for year in range(2020, 2024)]
        test = [_row(2024, 14, 13)]
        result = entrenar_y_evaluar(train, test)
        self.assertEqual(result["contrato"]["anios_prueba"], [2024])
        self.assertFalse(result["contrato"]["fuga_detectada"])
        self.assertEqual(result["metricas_prueba"]["random_forest"]["observaciones"], 1)

    def test_imputacion_se_ajusta_solo_con_entrenamiento(self) -> None:
        train = [_row(2020, 10, 9), _row(2021, 11, None), _row(2022, 12, 11), _row(2023, 13, 12)]
        test = [_row(2024, 14, None)]
        model = crear_modelos()["linear_regression"]
        x = [[row[column] for column in FEATURE_COLUMNS] for row in train]
        y = [row[TARGET] for row in train]
        model.fit(x, y)
        imputer = model.named_steps["imputer"]
        self.assertEqual(imputer.statistics_[1], 11)

    def test_resultado_es_reproducible_y_pipeline_se_puede_guardar(self) -> None:
        train = [_row(year, 10 + year - 2020, 9 + year - 2020) for year in range(2020, 2024)]
        test = [_row(2024, 14, 13)]
        first = entrenar_y_evaluar(train, test)
        second = entrenar_y_evaluar(train, test)
        self.assertEqual(first["modelo_seleccionado"], second["modelo_seleccionado"])
        self.assertEqual(first["predicciones"], second["predicciones"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.joblib"
            joblib.dump(first["modelo"], path)
            loaded = joblib.load(path)
            self.assertEqual(len(loaded.predict([[2024, 13, 13, 13, 100, 1, 1]])), 1)

    def test_predictores_no_incluyen_objetivo(self) -> None:
        self.assertNotIn(TARGET, FEATURE_COLUMNS)


if __name__ == "__main__":
    unittest.main()
