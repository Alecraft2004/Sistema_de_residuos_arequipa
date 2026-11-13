from __future__ import annotations

import io
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.main import app
from app.routers.etl import (
    administrador_actual_etl,
    cuenta_actual_etl,
    get_etl_session,
)


MINAM_CSV = (
    "UBIGEO;ANIO;DEPARTAMENTO;PROVINCIA;DISTRITO;POB_TOTAL_INEI\n"
    "010101;2024;Arequipa;Arequipa;Cercado;100\n"
).encode()


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self.session = session

    def __enter__(self) -> "FakeSession":
        return self.session

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False


class FakeSession:
    def __init__(
        self,
        fail_on_destinations: bool = False,
        scalar_values: list[object] | None = None,
        fail_on_hash_constraint: bool = False,
    ) -> None:
        self.added: list[object] = []
        self.rollbacks = 0
        self.fail_on_destinations = fail_on_destinations
        self.scalar_values = list(scalar_values or [42, None])
        self.fail_on_hash_constraint = fail_on_hash_constraint

    def scalar(self, _query):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    def add(self, item: object) -> None:
        self.added.append(item)

    def add_all(self, items) -> None:
        values = list(items)
        if self.fail_on_destinations and values:
            raise SQLAlchemyError("test rollback")
        self.added.extend(values)

    def flush(self) -> None:
        if self.fail_on_hash_constraint:
            raise IntegrityError(
                "insert",
                {},
                Exception("uq_importaciones_etl_hash_perfil"),
            )
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = 1
            if hasattr(item, "fecha_importacion") and item.fecha_importacion is None:
                item.fecha_importacion = datetime.now(timezone.utc)

    def rollback(self) -> None:
        self.rollbacks += 1


class ETLApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[cuenta_actual_etl] = lambda: {
            "usuario": "operador",
            "rol": "Operador",
        }
        app.dependency_overrides[administrador_actual_etl] = lambda: {
            "usuario": "admin",
            "rol": "Administrador",
        }
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_usuario_no_autenticado_recibe_401(self) -> None:
        app.dependency_overrides.clear()
        response = self.client.get("/etl/estadisticas")
        self.assertEqual(response.status_code, 401)

    def test_validar_minam_no_persiste(self) -> None:
        response = self.client.post(
            "/etl/validar",
            files={"archivo": ("minam.csv", io.BytesIO(MINAM_CSV), "text/csv")},
            data={"perfil_fuente": "MINAM_GENERACION_ANUAL"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["filas_validas"], 1)
        self.assertEqual(body["filas_rechazadas"], 0)
        self.assertEqual(body["perfil_fuente"], "MINAM_GENERACION_ANUAL")

    def test_perfil_inexistente_recibe_422(self) -> None:
        response = self.client.post(
            "/etl/validar",
            files={"archivo": ("minam.csv", io.BytesIO(MINAM_CSV), "text/csv")},
            data={"perfil_fuente": "NO_EXISTE"},
        )
        self.assertEqual(response.status_code, 422)

    def test_importacion_correcta_usa_destino_oficial(self) -> None:
        session = FakeSession()
        app.dependency_overrides[get_etl_session] = lambda: session
        response = self.client.post(
            "/etl/importar",
            files={"archivo": ("minam.csv", io.BytesIO(MINAM_CSV), "text/csv")},
            data={"perfil_fuente": "MINAM_GENERACION_ANUAL"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["estado"], "completado")
        self.assertTrue(any(item.__class__.__name__ == "GeneracionResiduoDistritoAnual" for item in session.added))

    def test_historial_paginado(self) -> None:
        session = object()
        app.dependency_overrides[get_etl_session] = lambda: session
        with patch(
            "app.routers.etl.listar_importaciones",
            return_value=([], 0),
        ):
            response = self.client.get("/etl/importaciones?pagina=2&tamano=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pagina"], 2)

    def test_fallo_de_carga_hace_rollback(self) -> None:
        from app.services.etl.api_service import importar_archivo
        from app.services.etl.ingestion_service import FilaArchivo
        from app.services.etl.source_profiles import MINAM_GENERACION_ANUAL
        from app.services.etl.validation_service import ResultadoValidacionETL

        session = FakeSession(fail_on_destinations=True)
        fila = FilaArchivo(2, {"UBIGEO": "010101", "ANIO": "2024"})
        proceso = {
            "nombre": "minam.csv",
            "tipo": "csv",
            "filas": (fila,),
            "resultado": ResultadoValidacionETL((fila,), (), ()),
            "transformados": (
                {
                    "datos": {"ubigeo": "010101", "anio": 2024},
                    "datos_originales": dict(fila.datos),
                },
            ),
            "hash_archivo": "a" * 64,
        }
        with self.assertRaises(RuntimeError):
            importar_archivo(
                session,
                archivo=proceso,
                perfil_id=MINAM_GENERACION_ANUAL.identificador,
                usuario_nombre="admin",
                hash_archivo="b" * 64,
            )
        self.assertEqual(session.rollbacks, 1)

    def test_importacion_duplicada_recibe_409_y_no_inserta(self) -> None:
        from app.models.etl import ImportacionETL

        existente = ImportacionETL(id=77)
        session = FakeSession(scalar_values=[42, existente])
        app.dependency_overrides[get_etl_session] = lambda: session
        response = self.client.post(
            "/etl/importar",
            files={"archivo": ("renamed.csv", io.BytesIO(MINAM_CSV), "text/csv")},
            data={"perfil_fuente": "MINAM_GENERACION_ANUAL"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("77", response.json()["detail"])
        self.assertEqual(session.added, [])

    def test_conflicto_unico_concurrente_recibe_409(self) -> None:
        from app.models.etl import ImportacionETL

        existente = ImportacionETL(id=88)
        session = FakeSession(
            scalar_values=[42, None, existente],
            fail_on_hash_constraint=True,
        )
        app.dependency_overrides[get_etl_session] = lambda: session
        response = self.client.post(
            "/etl/importar",
            files={"archivo": ("minam.csv", io.BytesIO(MINAM_CSV), "text/csv")},
            data={"perfil_fuente": "MINAM_GENERACION_ANUAL"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("88", response.json()["detail"])

    def test_hash_archivo_admite_null_para_importaciones_historicas(self) -> None:
        from app.models.etl import ImportacionETL

        self.assertTrue(ImportacionETL.__table__.c.hash_archivo.nullable)
        constraint = next(
            item
            for item in ImportacionETL.__table__.constraints
            if item.name == "uq_importaciones_etl_hash_perfil"
        )
        self.assertEqual(
            [column.name for column in constraint.columns],
            ["hash_archivo", "perfil_fuente"],
        )

    def test_estadisticas_reproduce_dos_importaciones_por_perfil(self) -> None:
        from app.services.etl.api_service import obtener_estadisticas

        session = Mock()
        session.scalar.side_effect = [2, 2, 0, 11310, 2118, 1]
        self.assertEqual(
            obtener_estadisticas(session),
            {
                "total_importaciones": 2,
                "importaciones_completadas": 2,
                "importaciones_fallidas": 0,
                "registros_importados_minam": 11310,
                "registros_importados_oefa": 2118,
                "registros_rechazados": 1,
            },
        )
