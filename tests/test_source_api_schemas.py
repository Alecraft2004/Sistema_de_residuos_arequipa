"""Pruebas de contratos Pydantic para las fuentes de datos."""

import pytest

from app.schemas.sources_api import (
    DiccionarioRutaResponse,
    OefaDetalleResponse,
    OefaListadoResponse,
    OefaResumenResponse,
    RutaResponse,
    RutasListadoResponse,
    RutasResumenResponse,
    ValorizacionRegistroResponse,
    ValorizacionResponse,
    ValorizacionResumenResponse,
)
from app.services.sources.oefa_service import (
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

def test_contrato_listado_oefa():
    registros = consultar_areas_oefa()

    respuesta = OefaListadoResponse.model_validate({
        "total_registros": len(registros),
        "limite": 100,
        "desplazamiento": 0,
        "datos": registros[:100],
    })

    assert respuesta.total_registros == len(registros)
    assert len(respuesta.datos) <= 100


def test_contrato_detalle_oefa():
    registros = consultar_areas_oefa()
    assert registros

    id_uf = registros[0].get("id_uf")
    assert id_uf is not None

    detalle = consultar_area_oefa(str(id_uf))

    respuesta = OefaDetalleResponse.model_validate({
        "total_registros": len(detalle),
        "datos": detalle,
    })

    assert respuesta.total_registros == len(detalle)
    assert respuesta.datos


def test_contrato_resumen_oefa():
    resumen = resumir_areas_oefa()

    respuesta = OefaResumenResponse.model_validate(resumen)

    assert respuesta.total_registros > 0
    assert respuesta.total_registros >= respuesta.con_ubigeo
    assert respuesta.total_registros >= respuesta.con_coordenadas


# ============================================================
# AREQUIPA RECICLA
# ============================================================

def test_contrato_listado_rutas():
    registros = consultar_rutas()

    respuesta = RutasListadoResponse.model_validate({
        "total_registros": len(registros),
        "datos": registros,
    })

    assert respuesta.total_registros == len(registros)


def test_contrato_detalle_ruta():
    registros = listar_rutas()
    assert registros

    codigo = registros[0]["codigo"]
    ruta = consultar_ruta(codigo)

    respuesta = RutaResponse.model_validate(ruta)

    assert respuesta.codigo == codigo


def test_contrato_resumen_rutas():
    resumen = resumir_rutas()

    respuesta = RutasResumenResponse.model_validate(resumen)

    assert respuesta.total_rutas > 0
    assert respuesta.rutas_con_datos_incompletos >= 0


def test_contrato_diccionario_rutas():
    registros = obtener_diccionario()

    respuestas = [
        DiccionarioRutaResponse.model_validate(registro)
        for registro in registros
    ]

    assert respuestas


# ============================================================
# VALORIZACIÓN
# ============================================================

@pytest.mark.parametrize("tipo", ["organica", "inorganica"])
def test_contrato_listado_valorizacion(tipo):
    registros = consultar_valorizacion(tipo=tipo)

    respuesta = ValorizacionResponse.model_validate({
        "total_registros": len(registros),
        "filtros": {
            "tipo": tipo,
            "anio": None,
            "departamento": None,
            "provincia": None,
            "ubigeo": None,
        },
        "datos": registros,
    })

    assert respuesta.total_registros == len(registros)
    assert respuesta.datos

    ValorizacionRegistroResponse.model_validate(registros[0])


@pytest.mark.parametrize("tipo", ["organica", "inorganica"])
def test_contrato_resumen_valorizacion(tipo):
    resumen = resumir_valorizacion(tipo=tipo)

    respuesta = ValorizacionResumenResponse.model_validate(resumen)

    assert respuesta.tipo == tipo
    assert respuesta.total_registros >= 0
    assert respuesta.unidad is None


