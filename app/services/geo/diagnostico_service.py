
"""Diagnóstico y priorización territorial de distritos."""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Any

from app.services.geo.territory_service import obtener_distritos
from app.services.ml.minam_prediction_service import future_predictions
from app.services.sources.oefa_service import listar_areas_oefa
from app.services.sources.valorizacion_service import consultar_valorizacion


class DiagnosticoServiceError(Exception):
    """Error controlado del diagnóstico territorial."""


def _texto(valor: Any) -> str:
    texto = str(valor or "").strip().casefold()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _ubigeo(valor: Any) -> str:
    return str(valor or "").strip().zfill(6)


def _clave_territorial(
    departamento: Any,
    provincia: Any,
    distrito: Any,
) -> tuple[str, str, str]:
    return (
        _texto(departamento),
        _texto(provincia),
        _texto(distrito),
    )


@lru_cache(maxsize=4)
def _construir_diagnostico(anio: int) -> tuple[dict[str, Any], ...]:
    try:
        cartografia = obtener_distritos(
            departamento="Arequipa",
            tolerancia=0.0001,
        )
        predicciones = future_predictions(departamento="Arequipa")

        areas_oefa = listar_areas_oefa()

        valorizacion_organica = consultar_valorizacion(
            tipo="organica",
            anio=anio,
            departamento="Arequipa",
        )
        valorizacion_inorganica = consultar_valorizacion(
            tipo="inorganica",
            anio=anio,
            departamento="Arequipa",
        )

    except Exception as error:
        raise DiagnosticoServiceError(
            "No se pudo construir el diagnóstico territorial."
        ) from error

    predicciones_por_ubigeo = {
        _ubigeo(item.get("ubigeo")): item
        for item in predicciones
    }

    organica_por_ubigeo = {
        _ubigeo(item.get("ubigeo")): item
        for item in valorizacion_organica
    }

    inorganica_por_ubigeo = {
        _ubigeo(item.get("ubigeo")): item
        for item in valorizacion_inorganica
    }

    oefa_por_territorio: dict[tuple[str, str, str], list[dict]] = {}

    for area in areas_oefa:
        if _texto(area.get("departamento")) != "arequipa":
            continue

        clave = _clave_territorial(
            area.get("departamento"),
            area.get("provincia"),
            area.get("distrito"),
        )
        oefa_por_territorio.setdefault(clave, []).append(area)

    resultados = []

    for feature in cartografia["features"]:
        propiedades = feature["properties"]
        codigo = _ubigeo(propiedades["ubigeo"])

        prediccion = predicciones_por_ubigeo.get(codigo)
        organica = organica_por_ubigeo.get(codigo)
        inorganica = inorganica_por_ubigeo.get(codigo)

        clave = _clave_territorial(
            propiedades["departamento"],
            propiedades["provincia"],
            propiedades["distrito"],
        )
        areas = oefa_por_territorio.get(clave, [])

        resultados.append({
            "ubigeo": codigo,
            "departamento": propiedades["departamento"],
            "provincia": propiedades["provincia"],
            "distrito": propiedades["distrito"],
            "anio_prediccion": (
                prediccion.get("anio_objetivo") if prediccion else None
            ),
            "generacion_predicha": (
                prediccion.get("generacion_predicha") if prediccion else None
            ),
            "modelo_minam": (
                prediccion.get("tipo_modelo") if prediccion else None
            ),
            "valorizacion_organica": (
                organica.get("valor") if organica else None
            ),
            "valorizacion_inorganica": (
                inorganica.get("valor") if inorganica else None
            ),
            "areas_degradadas_oefa": len(areas),
            "areas_oefa": [
                {
                    "id_uf": area.get("id_uf"),
                    "denominacion": area.get("denominacion"),
                    "categoria": area.get("categoria"),
                }
                for area in areas
            ],
            "disponibilidad": {
                "minam": prediccion is not None,
                "valorizacion_organica": organica is not None,
                "valorizacion_inorganica": inorganica is not None,
                "oefa": bool(areas),
            },
        })

    return tuple(resultados)


def obtener_diagnostico(
    anio: int = 2024,
    ubigeo: str | None = None,
) -> list[dict[str, Any]]:
    resultados = list(_construir_diagnostico(anio))

    if ubigeo:
        codigo = _ubigeo(ubigeo)
        resultados = [
            item for item in resultados
            if item["ubigeo"] == codigo
        ]

    return resultados


def priorizar_distritos(
    anio: int = 2024,
) -> list[dict[str, Any]]:
    resultados = obtener_diagnostico(anio)

    disponibles = [
        item for item in resultados
        if item["generacion_predicha"] is not None
    ]

    valores = sorted(
        float(item["generacion_predicha"])
        for item in disponibles
    )

    if not valores:
        return resultados

    def percentil(valor: float) -> float:
        menores = sum(v <= valor for v in valores)
        return round((menores / len(valores)) * 100, 2)

    for item in resultados:
        generacion = item["generacion_predicha"]

        if generacion is None:
            item["percentil_generacion"] = None
            item["prioridad_operativa"] = "Sin datos suficientes"
            continue

        p = percentil(float(generacion))
        item["percentil_generacion"] = p

        # Clasificación descriptiva, no predicción de acumulación.
        if p >= 75 and item["areas_degradadas_oefa"] > 0:
            prioridad = "Alta"
        elif p >= 50 or item["areas_degradadas_oefa"] > 0:
            prioridad = "Media"
        else:
            prioridad = "Baja"

        item["prioridad_operativa"] = prioridad

    orden = {"Alta": 0, "Media": 1, "Baja": 2}

    return sorted(
        resultados,
        key=lambda item: (
            orden.get(item["prioridad_operativa"], 3),
            -(item["percentil_generacion"] or 0),
        ),
    )


def obtener_resumen_diagnostico(anio: int = 2024) -> dict[str, Any]:
    resultados = obtener_diagnostico(anio)

    return {
        "departamento": "AREQUIPA",
        "anio_valorizacion": anio,
        "total_distritos": len(resultados),
        "distritos_con_prediccion_minam": sum(
            item["disponibilidad"]["minam"] for item in resultados
        ),
        "distritos_con_valorizacion_organica": sum(
            item["disponibilidad"]["valorizacion_organica"]
            for item in resultados
        ),
        "distritos_con_valorizacion_inorganica": sum(
            item["disponibilidad"]["valorizacion_inorganica"]
            for item in resultados
        ),
        "distritos_con_areas_oefa": sum(
            item["areas_degradadas_oefa"] > 0 for item in resultados
        ),
        "total_areas_oefa_relacionadas": sum(
            item["areas_degradadas_oefa"] for item in resultados
        ),
    }


def limpiar_cache_diagnostico() -> None:
    _construir_diagnostico.cache_clear()


def obtener_mapa_diagnostico(anio: int = 2024) -> dict[str, Any]:
    """
    Devuelve la cartografía de Arequipa enriquecida con el diagnóstico
    y la prioridad operativa de cada distrito.
    """
    cartografia = obtener_distritos(departamento="Arequipa")
    diagnosticos = priorizar_distritos(anio)

    diagnosticos_por_ubigeo = {
        item["ubigeo"]: item
        for item in diagnosticos
    }

    features = []

    for feature in cartografia["features"]:
        propiedades = feature["properties"]
        codigo = _ubigeo(propiedades.get("ubigeo"))
        diagnostico = diagnosticos_por_ubigeo.get(codigo)

        nuevas_propiedades = {
            **propiedades,
            "ubigeo": codigo,
            "diagnostico": diagnostico,
        }

        features.append({
            **feature,
            "properties": nuevas_propiedades,
        })

    return {
        "type": "FeatureCollection",
        "name": "diagnostico_territorial_arequipa",
        "anio_valorizacion": anio,
        "total_distritos": len(features),
        "features": features,
    }
    
def generar_plan_atencion(
    anio: int = 2024,
    limite: int = 20,
) -> dict[str, Any]:
    """
    Genera una lista ordenada de distritos para orientar la atención
    territorial según la priorización disponible.
    """
    resultados = priorizar_distritos(anio)
    seleccionados = resultados[:limite]

    plan = []

    for posicion, item in enumerate(seleccionados, start=1):
        prioridad = item["prioridad_operativa"]

        if prioridad == "Alta":
            recomendacion = (
                "Atención prioritaria y evaluación de las áreas degradadas."
            )
        elif prioridad == "Media":
            recomendacion = (
                "Programar seguimiento y evaluar necesidades de intervención."
            )
        elif prioridad == "Baja":
            recomendacion = (
                "Mantener seguimiento periódico."
            )
        else:
            recomendacion = (
                "Completar información antes de definir una intervención."
            )

        plan.append({
            "orden": posicion,
            "ubigeo": item["ubigeo"],
            "departamento": item["departamento"],
            "provincia": item["provincia"],
            "distrito": item["distrito"],
            "prioridad": prioridad,
            "generacion_predicha": item["generacion_predicha"],
            "percentil_generacion": item["percentil_generacion"],
            "areas_degradadas_oefa": item["areas_degradadas_oefa"],
            "recomendacion": recomendacion,
        })

    return {
        "departamento": "AREQUIPA",
        "anio_valorizacion": anio,
        "total_distritos_evaluados": len(resultados),
        "total_distritos_planificados": len(plan),
        "criterio": (
            "Orden basado en la prioridad operativa, el percentil de "
            "generación proyectada y la presencia de áreas degradadas OEFA."
        ),
        "alcance": (
            "Plan de atención territorial orientativo. "
            "No representa rutas físicas ni asignación de vehículos."
        ),
        "plan": plan,
    }
    
def obtener_dashboard_diagnostico(anio: int = 2024) -> dict[str, Any]:
    """
    Consolida los indicadores y prioridades territoriales
    para la pantalla principal del frontend.
    """
    resumen = obtener_resumen_diagnostico(anio)
    resultados = priorizar_distritos(anio)

    conteo_prioridades = {
        "alta": 0,
        "media": 0,
        "baja": 0,
        "sin_datos": 0,
    }

    for item in resultados:
        prioridad = item["prioridad_operativa"]

        if prioridad == "Alta":
            conteo_prioridades["alta"] += 1
        elif prioridad == "Media":
            conteo_prioridades["media"] += 1
        elif prioridad == "Baja":
            conteo_prioridades["baja"] += 1
        else:
            conteo_prioridades["sin_datos"] += 1

    principales_prioridades = [
        {
            "ubigeo": item["ubigeo"],
            "provincia": item["provincia"],
            "distrito": item["distrito"],
            "prioridad": item["prioridad_operativa"],
            "generacion_predicha": item["generacion_predicha"],
            "areas_degradadas_oefa": item["areas_degradadas_oefa"],
        }
        for item in resultados[:10]
    ]

    return {
        "departamento": "AREQUIPA",
        "anio_valorizacion": anio,
        "resumen": resumen,
        "distribucion_prioridades": conteo_prioridades,
        "total_distritos": len(resultados),
        "principales_prioridades": principales_prioridades,
    }