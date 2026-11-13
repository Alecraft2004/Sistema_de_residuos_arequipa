from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers.minam import cuenta_actual_minam
from app.services.ml.minam_prediction_service import (
    PredictionServiceError,
    clear_artifact_cache,
)


class MINAMApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[cuenta_actual_minam] = lambda: {
            "usuario": "operador",
            "rol": "Operador",
        }
        clear_artifact_cache()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        clear_artifact_cache()

    def test_estado_modelo_disponible(self) -> None:
        response = self.client.get("/kdd/minam/modelo/estado")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["disponible"])
        self.assertEqual(body["ultimo_anio_historico"], 2024)
        self.assertEqual(body["proximo_anio_prediccion"], 2025)

    def test_estado_modelo_no_disponible_no_rompe_la_api(self) -> None:
        clear_artifact_cache()
        with patch(
            "app.services.ml.minam_prediction_service._load_artifacts",
            side_effect=PredictionServiceError("artefactos ausentes"),
        ):
            response = self.client.get("/kdd/minam/modelo/estado")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["disponible"])

    def test_prediccion_nacional_futura_y_baseline(self) -> None:
        response = self.client.get("/kdd/minam/predicciones?anio_objetivo=2025")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1891)
        first = next(row for row in body if row["ubigeo"] == "100101")
        self.assertEqual(first["anio_historico"], 2024)
        self.assertEqual(first["anio_objetivo"], 2025)
        self.assertEqual(first["generacion_real_ultimo_anio"], first["generacion_predicha"])
        self.assertEqual(first["tipo_modelo"], "baseline_persistencia")

    def test_filtros_territoriales(self) -> None:
        response = self.client.get(
            "/kdd/minam/predicciones",
            params={
                "ubigeo": "100101",
                "departamento": "HUANUCO",
                "provincia": "HUANUCO",
                "distrito": "HUANUCO",
                "anio_objetivo": 2025,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_predicciones_arequipa(self) -> None:
        response = self.client.get("/kdd/minam/predicciones/arequipa?anio_objetivo=2025")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 109)
        self.assertTrue(all(row["departamento"] == "AREQUIPA" for row in response.json()))

    def test_ubigeo_inexistente(self) -> None:
        response = self.client.get("/kdd/minam/predicciones/999999?anio_objetivo=2025")
        self.assertEqual(response.status_code, 404)

    def test_anio_historico_no_es_prediccion_futura(self) -> None:
        response = self.client.get("/kdd/minam/predicciones?anio_objetivo=2024")
        self.assertEqual(response.status_code, 422)

    def test_evaluacion_2024_es_historica(self) -> None:
        response = self.client.get("/kdd/minam/evaluacion/2024")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1891)
        self.assertEqual(body[0]["resultado"], "evaluacion_historica_2024")

    def test_metricas_exponen_evaluacion_y_validacion(self) -> None:
        response = self.client.get("/kdd/minam/modelo/metricas")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["evaluacion_nacional_2024"]["observaciones"], 1891)
        self.assertEqual(body["evaluacion_arequipa_2024"]["observaciones"], 109)
        self.assertIn("baseline_persistencia", body["validacion_temporal"])

    def test_sin_autenticacion_recibe_401(self) -> None:
        app.dependency_overrides.clear()
        response = self.client.get("/kdd/minam/modelo/estado")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
