"""Planificador demostrativo de rutas de recolección."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from ml_service import predecir_residuos

COORDENADAS = {
    "Centro Histórico": (-16.3989, -71.5369),
    "La Libertad": (-16.3540, -71.5670),
    "Zamácola": (-16.3452, -71.5630),
    "Mariscal Cáceres": (-16.4310, -71.5110),
    "Miguel Grau": (-16.4250, -71.5050),
}
BASE_MUNICIPAL = (-16.3988, -71.5350)
ORDEN_PRIORIDAD = {"Alta": 0, "Media": 1, "Baja": 2}


def priorizar_zonas(zonas, dia_semana: int, hora: int) -> list[dict]:
    resultados = []
    for indice, zona in enumerate(zonas):
        resultado = predecir_residuos(
            zona.poblacion_estimada, dia_semana, hora, indice % 4, int(zona.poblacion_estimada * 0.025)
        )
        resultados.append({"zona": zona.nombre, "distrito": zona.distrito.nombre, **resultado})
    return sorted(resultados, key=lambda fila: (ORDEN_PRIORIDAD[fila["prioridad"]], -fila["cantidad_estimada_kg"]))


def _distancia_km(origen: tuple[float, float], destino: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*origen, *destino))
    valor = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(valor))


def construir_ruta(prioridades: list[dict], capacidad_kg: int = 5000) -> dict:
    seleccionadas, carga, recorrido, ubicacion_actual = [], 0, 0.0, BASE_MUNICIPAL
    pendientes = prioridades.copy()
    while pendientes:
        candidatas = [fila for fila in pendientes if carga + fila["cantidad_estimada_kg"] <= capacidad_kg]
        if not candidatas:
            break
        siguiente = min(candidatas, key=lambda fila: _distancia_km(ubicacion_actual, COORDENADAS[fila["zona"]]))
        recorrido += _distancia_km(ubicacion_actual, COORDENADAS[siguiente["zona"]])
        ubicacion_actual = COORDENADAS[siguiente["zona"]]
        carga += siguiente["cantidad_estimada_kg"]
        seleccionadas.append(siguiente)
        pendientes.remove(siguiente)
    recorrido += _distancia_km(ubicacion_actual, BASE_MUNICIPAL)
    return {"zonas": seleccionadas, "carga": carga, "distancia": round(recorrido, 1), "capacidad": capacidad_kg}


