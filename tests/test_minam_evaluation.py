from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.ml.minam_evaluation_service import evaluar_predicciones, leer_predicciones


def _row(actual: float, predicted: float, department: str = "AREQUIPA") -> dict:
    return {
        "ubigeo": "010101",
        "departamento": department,
        "provincia": "AREQUIPA",
        "distrito": "CERCADO",
        "anio_objetivo": 2024,
        "generacion_real": actual,
        "generacion_predicha": predicted,
    }


class MINAMEvaluationTestCase(unittest.TestCase):
    def test_calcula_errores_y_metricas(self) -> None:
        report = evaluar_predicciones([_row(100, 90), _row(200, 220)])
        self.assertAlmostEqual(report["metricas_nacionales"]["mae"], 15)
        self.assertEqual(report["residuos"]["sobreestimaciones"], 1)
        self.assertEqual(report["residuos"]["subestimaciones"], 1)

    def test_evita_division_por_cero(self) -> None:
        report = evaluar_predicciones([_row(0, 5)])
        row = report["predicciones_evaluadas"][0]
        self.assertIsNone(row["error_porcentual"])

    def test_metricas_departamento_y_arequipa(self) -> None:
        report = evaluar_predicciones([_row(100, 90), _row(200, 220, "CUSCO")])
        self.assertEqual(report["metricas_arequipa"]["observaciones"], 1)
        self.assertIn("CUSCO", report["metricas_departamento"])

    def test_mayores_y_menores_errores(self) -> None:
        rows = [_row(100, 90), _row(100, 101), _row(100, 150)]
        report = evaluar_predicciones(rows)
        self.assertEqual(report["peores_20"][0]["error_absoluto"], 50)
        self.assertEqual(report["mejores_20"][0]["error_absoluto"], 1)

    def test_detecta_inconsistencia_de_error_precalculado(self) -> None:
        row = _row(100, 90)
        row["error_absoluto"] = 999
        report = evaluar_predicciones([row])
        self.assertEqual(report["errores_precalculados_inconsistentes"], 1)

    def test_lectura_reproducible_no_modifica_archivo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.csv"
            path.write_text(
                "ubigeo,departamento,provincia,distrito,anio_objetivo,generacion_real,generacion_predicha\n"
                "010101,AREQUIPA,AREQUIPA,CERCADO,2024,100,90\n",
                encoding="utf-8",
            )
            before = path.read_bytes()
            first = evaluar_predicciones(leer_predicciones(path))
            second = evaluar_predicciones(leer_predicciones(path))
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(first["metricas_nacionales"], second["metricas_nacionales"])


if __name__ == "__main__":
    unittest.main()
