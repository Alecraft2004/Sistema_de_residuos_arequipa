from __future__ import annotations

import unittest
from decimal import Decimal

from app.services.kdd.preprocessing_service import evaluar_calidad_minam
from app.services.kdd.selection_service import MINAM_LEAKAGE_COLUMNS
from app.services.kdd.transformation_service import (
    crear_diccionario_minam,
    transformar_minam,
)


def _record(
    ubigeo: str = "010101",
    year: int = 2019,
    total: int = 100,
    urban: int = 80,
    rural: int = 20,
    target: str = "10.5",
) -> dict:
    return {
        "ubigeo": ubigeo,
        "departamento": "Arequipa",
        "provincia": "Arequipa",
        "distrito": "Cercado",
        "anio": year,
        "poblacion_total_inei": Decimal(total),
        "poblacion_urbana_inei": Decimal(urban),
        "poblacion_rural_inei": Decimal(rural),
        "generacion_municipal_t_anio": Decimal(target),
    }


class KDDPreprocessingTestCase(unittest.TestCase):
    def test_detecta_duplicados_ubigeo_anio(self) -> None:
        report = evaluar_calidad_minam([_record(), _record()])
        self.assertEqual(report["duplicados_por_ubigeo_anio"]["filas_excedentes"], 1)

    def test_reporta_valores_faltantes_y_tipos(self) -> None:
        row = _record()
        row["distrito"] = None
        row["poblacion_total_inei"] = None
        report = evaluar_calidad_minam([row])
        self.assertEqual(report["valores_faltantes"]["distrito"], 1)
        self.assertEqual(report["valores_faltantes"]["poblacion_total_inei"], 1)
        self.assertEqual(report["tipos_observados"]["anio"], ["int"])

    def test_reporta_negativos_sin_eliminarlos(self) -> None:
        row = _record(total=-1, urban=0, rural=0)
        report = evaluar_calidad_minam([row])
        self.assertEqual(report["valores_negativos"]["poblacion_total_inei"], 1)
        self.assertEqual(report["filas_despues"], 1)
        self.assertEqual(report["filas_excluidas"], 0)

    def test_reporta_cobertura_temporal(self) -> None:
        report = evaluar_calidad_minam(
            [_record(year=2019), _record(year=2020), _record(year=2024)]
        )
        self.assertEqual(report["cobertura_temporal"]["anios"], [2019, 2020, 2024])
        self.assertEqual(report["cobertura_temporal"]["por_ubigeo"][3], 1)

    def test_separa_entrenamiento_y_prueba_por_anio(self) -> None:
        records = [_record(year=2023), _record(year=2024)]
        report = evaluar_calidad_minam(records)
        rows = transformar_minam(records, report)
        self.assertEqual(
            [row["particion_temporal"] for row in rows],
            ["entrenamiento", "prueba"],
        )

    def test_no_incluye_variables_con_fuga_en_predictoras(self) -> None:
        dictionary = crear_diccionario_minam()
        self.assertTrue(set(MINAM_LEAKAGE_COLUMNS).isdisjoint(dictionary["predictoras"]))

    def test_brecha_solo_se_crea_con_poblacion_consistente(self) -> None:
        records = [_record()]
        report = evaluar_calidad_minam(records)
        transformed = transformar_minam(records, report)
        self.assertEqual(transformed[0]["brecha_poblacion"], 0)

        inconsistent = [_record(total=101)]
        inconsistent_report = evaluar_calidad_minam(inconsistent)
        transformed_inconsistent = transformar_minam(inconsistent, inconsistent_report)
        self.assertNotIn("brecha_poblacion", transformed_inconsistent[0])


if __name__ == "__main__":
    unittest.main()
