from __future__ import annotations

import unittest

from app.services.kdd.feature_engineering_service import (
    LEAKAGE_COLUMNS,
    TARGET_COLUMN,
    construir_caracteristicas,
    generar_reporte_caracteristicas,
    validar_caracteristicas,
)


def _row(ubigeo: str, year: int, generation: float, population: float) -> dict:
    return {
        "ubigeo": ubigeo,
        "departamento": "Arequipa",
        "provincia": "Arequipa",
        "distrito": ubigeo,
        "anio": year,
        "poblacion_total_inei": population,
        "generacion_municipal_t_anio": generation,
    }


class KDDFeatureEngineeringTestCase(unittest.TestCase):
    def test_calcula_rezagos_dentro_del_mismo_ubigeo(self) -> None:
        rows = construir_caracteristicas(
            [
                _row("A", 2019, 10, 100),
                _row("A", 2020, 12, 110),
                _row("A", 2021, 15, 120),
                _row("B", 2020, 99, 900),
            ]
        )
        current = next(row for row in rows if row["ubigeo"] == "A" and row["anio_objetivo"] == 2021)
        other = next(row for row in rows if row["ubigeo"] == "B")
        self.assertEqual(current["generacion_lag_1"], 12)
        self.assertEqual(current["generacion_lag_2"], 10)
        self.assertEqual(current["poblacion_lag_1"], 110)
        self.assertIsNone(other["generacion_lag_1"])

    def test_calcula_variacion_y_tendencia_con_historial_previo(self) -> None:
        rows = construir_caracteristicas(
            [_row("A", 2019, 10, 100), _row("A", 2020, 12, 110), _row("A", 2021, 15, 120), _row("A", 2022, 18, 130)]
        )
        current = rows[-1]
        self.assertEqual(current["variacion_anual_generacion"], 3)
        self.assertEqual(current["tendencia_generacion_3_anios"], 2.5)

    def test_rezagos_sin_historial_quedan_nulos(self) -> None:
        rows = construir_caracteristicas([_row("A", 2021, 15, 120)])
        self.assertIsNone(rows[0]["generacion_lag_1"])
        self.assertIsNone(rows[0]["tendencia_generacion_3_anios"])

    def test_valida_claves_y_precedencia_temporal(self) -> None:
        rows = construir_caracteristicas(
            [_row("A", 2019, 10, 100), _row("A", 2020, 12, 110)]
        )
        validation = validar_caracteristicas(rows)
        self.assertTrue(validation["claves_unicas_ubigeo_anio_objetivo"])
        self.assertEqual(validation["errores_generacion_lag_1"], 0)
        self.assertFalse(validation["fuga_temporal_detectada"])

    def test_reporta_separacion_2020_2023_y_2024(self) -> None:
        source = [_row("A", 2019, 10, 100), _row("A", 2020, 12, 110), _row("A", 2024, 18, 140)]
        features = construir_caracteristicas(source)
        report = generar_reporte_caracteristicas(source, features, validar_caracteristicas(features))
        self.assertEqual(report["filas_entrenamiento"], 1)
        self.assertEqual(report["filas_prueba"], 1)
        self.assertEqual(report["objetivos_prueba"], [2024])

    def test_columnas_de_fuga_no_son_predictoras(self) -> None:
        validation = validar_caracteristicas(
            construir_caracteristicas([_row("A", 2019, 10, 100)])
        )
        predictors = set(validation["columnas_predictoras"])
        self.assertTrue(predictors.isdisjoint(LEAKAGE_COLUMNS))
        self.assertNotIn(TARGET_COLUMN, predictors)


if __name__ == "__main__":
    unittest.main()
