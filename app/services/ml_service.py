"""Motor predictivo demostrativo para la gestión de residuos urbanos."""

from __future__ import annotations

import random

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, r2_score

CARACTERISTICAS = [
    "poblacion_estimada",
    "dia_semana",
    "hora",
    "dias_sin_recoleccion",
    "acumulacion_previa_kg",
]


def _generar_datos_demostrativos() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Genera datos sintéticos reproducibles. No representan información oficial."""
    generador = random.Random(42)
    caracteristicas: list[list[float]] = []
    cantidades: list[float] = []
    niveles: list[str] = []

    for _ in range(600):
        poblacion = generador.randint(9000, 50000)
        dia = generador.randint(0, 6)
        hora = generador.randint(0, 23)
        dias_sin_recoleccion = generador.randint(0, 5)
        acumulacion_previa = generador.randint(20, 1800)
        fin_semana = 150 if dia in (5, 6) else 0
        hora_pico = 120 if 17 <= hora <= 22 else 0
        ruido = generador.randint(-90, 90)
        cantidad = max(
            30,
            0.018 * poblacion
            + 0.65 * acumulacion_previa
            + 125 * dias_sin_recoleccion
            + fin_semana
            + hora_pico
            + ruido,
        )
        nivel = "Bajo" if cantidad < 700 else "Medio" if cantidad < 1400 else "Alto"
        caracteristicas.append([poblacion, dia, hora, dias_sin_recoleccion, acumulacion_previa])
        cantidades.append(cantidad)
        niveles.append(nivel)

    return np.array(caracteristicas), np.array(cantidades), np.array(niveles)


_X, _Y_CANTIDAD, _Y_NIVEL = _generar_datos_demostrativos()
MODELO_CANTIDAD = RandomForestRegressor(n_estimators=180, random_state=42, min_samples_leaf=2)
MODELO_NIVEL = RandomForestClassifier(n_estimators=180, random_state=42, min_samples_leaf=2)
MODELO_CANTIDAD.fit(_X, _Y_CANTIDAD)
MODELO_NIVEL.fit(_X, _Y_NIVEL)


def obtener_metricas_modelo() -> dict[str, float]:
    """Métricas sobre los datos demostrativos de entrenamiento."""
    return {
        "r2": round(float(r2_score(_Y_CANTIDAD, MODELO_CANTIDAD.predict(_X))) * 100, 1),
        "exactitud": round(float(accuracy_score(_Y_NIVEL, MODELO_NIVEL.predict(_X))) * 100, 1),
    }


def predecir_residuos(
    poblacion_estimada: int,
    dia_semana: int,
    hora: int,
    dias_sin_recoleccion: int,
    acumulacion_previa_kg: int,
) -> dict[str, str | int]:
    entrada = np.array(
        [[poblacion_estimada, dia_semana, hora, dias_sin_recoleccion, acumulacion_previa_kg]]
    )
    cantidad = max(1, round(float(MODELO_CANTIDAD.predict(entrada)[0])))
    nivel = str(MODELO_NIVEL.predict(entrada)[0])

    if nivel == "Alto" or dias_sin_recoleccion >= 4:
        prioridad = "Alta"
        recomendacion = "Programar recolección prioritaria antes del siguiente periodo de alta demanda."
    elif nivel == "Medio":
        prioridad = "Media"
        recomendacion = "Programar recolección durante el siguiente turno operativo."
    else:
        prioridad = "Baja"
        recomendacion = "Mantener el recorrido programado y realizar seguimiento de la zona."

    return {
        "cantidad_estimada_kg": cantidad,
        "nivel": nivel,
        "prioridad": prioridad,
        "recomendacion": recomendacion,
    }
