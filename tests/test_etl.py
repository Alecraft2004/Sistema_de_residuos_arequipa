from __future__ import annotations

import io
import unittest
from datetime import date

from openpyxl import Workbook

from app.schemas.etl import ConfiguracionColumnasETL
from app.services.etl.ingestion_service import (
    EmptyFileError,
    UnsupportedFileTypeError,
    leer_archivo,
)
from app.services.etl.source_profiles import (
    MINAM_GENERACION_ANUAL,
    OEFA_AREAS_DEGRADADAS,
)
from app.services.etl.transformation_service import transformar_fila
from app.services.etl.validation_service import validar_archivo


class ETLServicesTestCase(unittest.TestCase):
    def test_lee_csv_valido(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(b"fecha,cantidad\n2026-01-01,10\n"),
            "residuos.csv",
            "text/csv",
        )
        self.assertEqual(archivo.columnas, ("fecha", "cantidad"))
        self.assertEqual(archivo.filas[0].datos["cantidad"], "10")

    def test_lee_xlsx_valido(self) -> None:
        libro = Workbook()
        hoja = libro.active
        hoja.append(["fecha", "cantidad"])
        hoja.append(["2026-01-01", 10])
        contenido = io.BytesIO()
        libro.save(contenido)
        contenido.seek(0)

        archivo = leer_archivo(
            contenido,
            "residuos.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(archivo.filas[0].datos["cantidad"], 10)

    def test_rechaza_archivo_vacio(self) -> None:
        with self.assertRaises(EmptyFileError):
            leer_archivo(io.BytesIO(b""), "residuos.csv", "text/csv")

    def test_rechaza_extension_no_permitida(self) -> None:
        with self.assertRaises(UnsupportedFileTypeError):
            leer_archivo(io.BytesIO(b"data"), "residuos.xls", "application/octet-stream")

    def test_informa_columnas_no_reconocidas(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(b"fecha,extra\n2026-01-01,valor\n"),
            "residuos.csv",
            "text/csv",
        )
        resultado = validar_archivo(
            archivo,
            ConfiguracionColumnasETL(mapeo_columnas={"fecha": "fecha"}),
        )
        self.assertEqual(resultado.columnas_no_reconocidas, ("extra",))

    def test_rechaza_nulos_negativos_fechas_invalidas_y_duplicados(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(
                b"fecha,cantidad,id\n"
                b"2026-01-01,10,1\n"
                b"fecha-invalida,-2,2\n"
                b"2026-01-01,10,1\n"
            ),
            "residuos.csv",
            "text/csv",
        )
        resultado = validar_archivo(
            archivo,
            ConfiguracionColumnasETL(
                mapeo_columnas={"fecha": "fecha", "cantidad": "cantidad", "id": "id"},
                columnas_obligatorias={"fecha", "cantidad"},
                columnas_no_negativas={"cantidad"},
                columnas_fecha={"fecha"},
                tipos={"cantidad": "number"},
                claves_duplicado=["id"],
            ),
        )
        self.assertEqual(len(resultado.filas_validas), 1)
        self.assertEqual(len(resultado.filas_rechazadas), 2)
        motivos = " ".join(rechazo.motivo for rechazo in resultado.filas_rechazadas)
        self.assertIn("fecha", motivos)
        self.assertIn("negativo", motivos)
        self.assertIn("duplicado", motivos)

    def test_rechaza_valores_nulos_en_columnas_obligatorias(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(b"fecha,cantidad\n2026-01-01,\n"),
            "residuos.csv",
            "text/csv",
        )
        resultado = validar_archivo(
            archivo,
            ConfiguracionColumnasETL(
                columnas_obligatorias={"cantidad"},
            ),
        )
        self.assertEqual(len(resultado.filas_rechazadas), 1)
        self.assertIn("obligatorio", resultado.filas_rechazadas[0].motivo)

    def test_lee_minam_con_latin1_separador_y_ubigeo_textual(self) -> None:
        contenido = (
            " UBIGEO ; ANIO ; DISTRITO ; POB_TOTAL_INEI\n"
            "010101 ; 2024 ; Arequipa ; 100\n"
        ).encode("latin-1")
        archivo = leer_archivo(
            io.BytesIO(contenido),
            "minam.csv",
            "text/csv",
            delimiter=MINAM_GENERACION_ANUAL.separador,
            encoding=MINAM_GENERACION_ANUAL.codificacion,
        )
        self.assertEqual(archivo.columnas[0], "UBIGEO")
        self.assertEqual(archivo.encabezados_originales[0], " UBIGEO ")
        self.assertEqual(archivo.filas[0].datos["UBIGEO"], "010101")
        self.assertEqual(archivo.codificacion, "latin-1")

    def test_valida_minam_y_detecta_faltantes_y_duplicado_ubigeo_anio(self) -> None:
        contenido = (
            "UBIGEO;ANIO;DEPARTAMENTO;PROVINCIA;DISTRITO;POB_TOTAL_INEI\n"
            "010101;2024;Arequipa;Arequipa;Cercado;100\n"
            "010101;2024;Arequipa;Arequipa;Cercado;-1\n"
        ).encode("latin-1")
        archivo = leer_archivo(
            io.BytesIO(contenido),
            "minam.csv",
            delimiter=MINAM_GENERACION_ANUAL.separador,
            encoding=MINAM_GENERACION_ANUAL.codificacion,
        )
        resultado = validar_archivo(archivo, MINAM_GENERACION_ANUAL.configuracion())
        self.assertEqual(len(resultado.filas_validas), 1)
        self.assertEqual(len(resultado.filas_rechazadas), 1)
        self.assertIn("negativo", resultado.filas_rechazadas[0].motivo)

    def test_transformacion_minam_conserva_origen_y_tipa_solo_configurados(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(
                b"UBIGEO;ANIO;DISTRITO\n010101;2024;Arequipa\n"
            ),
            "minam.csv",
            delimiter=";",
            encoding="utf-8",
        )
        transformado = transformar_fila(
            archivo.filas[0], MINAM_GENERACION_ANUAL.configuracion()
        )
        self.assertEqual(transformado["datos"]["ubigeo"], "010101")
        self.assertEqual(transformado["datos"]["anio"], 2024)
        self.assertEqual(transformado["datos_originales"]["UBIGEO"], "010101")
        self.assertEqual(transformado["perfil_fuente"], "MINAM_GENERACION_ANUAL")

    def test_perfiles_minam_y_oefa_no_comparten_mapeos(self) -> None:
        self.assertNotEqual(
            MINAM_GENERACION_ANUAL.identificador,
            OEFA_AREAS_DEGRADADAS.identificador,
        )
        self.assertIn("generacion_municipal_t_anio", MINAM_GENERACION_ANUAL.tipos)
        self.assertIn("area_m2", OEFA_AREAS_DEGRADADAS.tipos)
        self.assertNotIn("area_m2", MINAM_GENERACION_ANUAL.tipos)

    def test_valida_booleanos_y_deja_coordenadas_opcionales(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(
                b"\xef\xbb\xbfUBIGEO,DENOMINACION,SEGREGACION,ESTE,NORTE\n"
                b"010101,Relleno,S\xc3\xad,,\n"
            ),
            "oefa.csv",
            encoding="utf-8-sig",
        )
        resultado = validar_archivo(archivo, OEFA_AREAS_DEGRADADAS.configuracion())
        self.assertEqual(len(resultado.filas_validas), 1)
        self.assertEqual(archivo.columnas[0], "UBIGEO")
        self.assertTrue(archivo.encabezados_originales[0].startswith("\ufeff"))

    def test_informa_columnas_obligatorias_faltantes_del_perfil(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(b"UBIGEO\n010101\n"),
            "minam.csv",
            delimiter=";",
            encoding="utf-8",
        )
        resultado = validar_archivo(archivo, MINAM_GENERACION_ANUAL.configuracion())
        self.assertIn("anio", resultado.columnas_faltantes)
        self.assertIn("distrito", resultado.columnas_faltantes)

    def test_transforma_fechas_minam_compactas_y_conserva_origen(self) -> None:
        for valor, esperado in (
            ("18122025", date(2025, 12, 18)),
            ("20240410", date(2024, 4, 10)),
            ("18/12/2025", date(2025, 12, 18)),
            ("2024-04-10", date(2024, 4, 10)),
        ):
            archivo = leer_archivo(
                io.BytesIO(f"FECHA_CORTE\n{valor}\n".encode()),
                "minam.csv",
                delimiter=";",
                encoding="utf-8",
            )
            transformado = transformar_fila(
                archivo.filas[0], MINAM_GENERACION_ANUAL.configuracion()
            )
            self.assertEqual(transformado["datos"]["fecha_corte"], esperado)
            self.assertEqual(transformado["datos_originales"]["FECHA_CORTE"], valor)

    def test_rechaza_fecha_compacta_invalida(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(b"FECHA_CORTE\n18132025\n"),
            "minam.csv",
            delimiter=";",
            encoding="utf-8",
        )
        resultado = validar_archivo(archivo, MINAM_GENERACION_ANUAL.configuracion())
        self.assertEqual(len(resultado.filas_rechazadas), 1)

    def test_normaliza_bom_comillas_y_booleanos_oefa(self) -> None:
        contenido = (
            b'\xef\xbb\xbf"UBIGEO",DENOMINACION,MUNICIPALIDAD_DISPONEN,'
            b'SEGREGACION,CRIANZA_ANIMAL\n'
            b',Relleno,Municipalidad distrital,No Precisa,Si\n'
        )
        archivo = leer_archivo(
            io.BytesIO(contenido),
            "oefa.csv",
            encoding="utf-8-sig",
        )
        self.assertEqual(archivo.columnas[0], "UBIGEO")
        resultado = validar_archivo(archivo, OEFA_AREAS_DEGRADADAS.configuracion())
        self.assertEqual(len(resultado.filas_validas), 1)
        transformado = transformar_fila(
            archivo.filas[0], OEFA_AREAS_DEGRADADAS.configuracion()
        )
        self.assertIsNone(transformado["datos"]["ubigeo"])
        self.assertEqual(
            transformado["datos"]["municipalidad_disponen"],
            "Municipalidad distrital",
        )
        self.assertIsNone(transformado["datos"]["segregacion"])
        self.assertTrue(transformado["datos"]["crianza_animal"])
        self.assertEqual(transformado["datos_originales"]["SEGREGACION"], "No Precisa")

    def test_oefa_no_exige_ubigeo_y_conserva_cantidad_vacia(self) -> None:
        archivo = leer_archivo(
            io.BytesIO(b"UBIGEO,DENOMINACION,CANT_MUNI_DISPONEN\n,Relleno,\n"),
            "oefa.csv",
            encoding="utf-8",
        )
        resultado = validar_archivo(archivo, OEFA_AREAS_DEGRADADAS.configuracion())
        self.assertEqual(len(resultado.filas_validas), 1)
        transformado = transformar_fila(
            archivo.filas[0], OEFA_AREAS_DEGRADADAS.configuracion()
        )
        self.assertIsNone(transformado["datos"]["ubigeo"])
        self.assertIsNone(transformado["datos"]["cantidad_municipalidades_disponen"])


if __name__ == "__main__":
    unittest.main()
