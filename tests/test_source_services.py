
"""Pruebas de lectura y consulta de fuentes oficiales."""

import pytest

from app.services.sources.oefa_service import (
    listar_areas_oefa,
    consultar_areas_oefa,
    consultar_area_oefa,
    resumir_areas_oefa,
)

from app.services.sources.rutas_service import (
    listar_rutas,
    consultar_rutas,
    consultar_ruta,
    obtener_diccionario,
    resumir_rutas,
)

from app.services.sources.valorizacion_service import (
    consultar_valorizacion,
    resumir_valorizacion,
)


# ============================================================
# OEFA
# ============================================================

def test_oefa_carga_inventario_completo():
    registros = listar_areas_oefa()

    assert len(registros) == 2119
    assert registros[0]["id_uf"] == "UF0010607"


def test_oefa_conserva_datos_territoriales_sin_inventar_ubigeo():
    registros = listar_areas_oefa()

    assert registros[0]["departamento"] == "Amazonas"
    assert registros[0]["provincia"] == "Bagua"
    assert registros[0]["ubigeo"] is None


def test_oefa_resumen_por_categoria():
    resumen = resumir_areas_oefa()

    assert resumen["total_registros"] == 2119
    assert resumen["por_categoria"]["Recuperación"] == 2067
    assert resumen["por_categoria"]["Reconversión"] == 52
    assert resumen["con_ubigeo"] == 0
    assert resumen["con_coordenadas"] == 0


def test_oefa_filtra_por_departamento():
    registros = consultar_areas_oefa(departamento="Arequipa")

    assert len(registros) == 104
    assert all(
        registro["departamento"] == "Arequipa"
        for registro in registros
    )


def test_oefa_consulta_por_identificador():
    registros = consultar_area_oefa("UF0010607")

    assert len(registros) == 1
    assert registros[0]["denominacion"] == (
        "Botadero Sector La Curva-Pasamayito"
    )


def test_oefa_filtro_sin_resultados():
    registros = consultar_areas_oefa(
        departamento="Departamento inexistente"
    )

    assert registros == []


# ============================================================
# RUTAS AREQUIPA RECICLA
# ============================================================

def test_rutas_carga_25_registros():
    registros = listar_rutas()

    assert len(registros) == 25


def test_rutas_normaliza_codigo():
    ruta = consultar_ruta("RD -01")

    assert ruta is not None
    assert ruta["codigo"] == "RD-01"
    assert ruta["numero"] == 1


def test_rutas_conserva_datos_incompletos():
    resumen = resumir_rutas()

    assert resumen["total_rutas"] == 25
    assert resumen["rutas_con_datos_incompletos"] == 3


def test_rutas_filtra_por_dia():
    registros = consultar_rutas(dia="lunes")

    assert len(registros) == 8
    assert all(
        "lunes" in registro["dia"].casefold()
        for registro in registros
    )


def test_rutas_diccionario():
    diccionario = obtener_diccionario()

    assert len(diccionario) == 7


def test_ruta_inexistente():
    assert consultar_ruta("RD-999") is None


# ============================================================
# VALORIZACIÓN
# ============================================================

@pytest.mark.parametrize("tipo", ["organica", "inorganica"])
def test_valorizacion_arequipa_2024(tipo):
    registros = consultar_valorizacion(
        tipo=tipo,
        anio=2024,
        departamento="AREQUIPA",
    )

    assert len(registros) == 109
    assert all(registro["anio"] == 2024 for registro in registros)
    assert all(
        registro["departamento"] == "AREQUIPA"
        for registro in registros
    )


@pytest.mark.parametrize("tipo", ["organica", "inorganica"])
def test_valorizacion_resumen(tipo):
    resumen = resumir_valorizacion(
        tipo=tipo,
        anio=2024,
        departamento="AREQUIPA",
    )

    assert resumen["total_registros"] == 109
    assert resumen["tipo"] == tipo
    assert resumen["unidad"] is None


def test_valorizacion_filtro_por_ubigeo():
    registros = consultar_valorizacion(
        tipo="organica",
        anio=2024,
        ubigeo="040102",
    )

    assert len(registros) == 1
    assert registros[0]["ubigeo"] == "040102"

