from __future__ import annotations

import math
from typing import Any, Mapping

from app.services.kdd.preprocessing_service import validar_particion_temporal


def _number(value: Any) -> float | None:
    return None if value is None else float(value)


def transformar_minam(
    records: list[Mapping[str, Any]],
    quality_report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Añade variables derivadas sin sustituir las variables originales."""
    permite_brecha = bool(
        quality_report["consistencia_poblacion"]["brecha_permitida"]
    )
    first_year = min(
        int(record["anio"]) for record in records if record.get("anio") is not None
    )
    transformed: list[dict[str, Any]] = []
    for record in records:
        row = dict(record)
        total = _number(record.get("poblacion_total_inei"))
        urban = _number(record.get("poblacion_urbana_inei"))
        rural = _number(record.get("poblacion_rural_inei"))
        target = _number(record.get("generacion_municipal_t_anio"))
        row["anio_desde_inicio"] = int(record["anio"]) - first_year
        row["particion_temporal"] = validar_particion_temporal(record["anio"])
        row["log1p_poblacion_total_inei"] = (
            math.log1p(total) if total is not None and total >= 0 else None
        )
        row["log1p_generacion_municipal_t_anio"] = (
            math.log1p(target) if target is not None and target >= 0 else None
        )
        if permite_brecha and total is not None and urban is not None and rural is not None:
            row["brecha_poblacion"] = total - urban - rural
        transformed.append(row)
    return transformed


def crear_diccionario_minam() -> dict[str, Any]:
    return {
        "dataset": "MINAM_GENERACION_ANUAL",
        "unidad_observacion": "una fila por UBIGEO + ANIO",
        "predictoras": [
            "ubigeo",
            "departamento",
            "provincia",
            "distrito",
            "anio",
            "poblacion_total_inei",
            "poblacion_urbana_inei",
            "poblacion_rural_inei",
        ],
        "objetivo": "generacion_municipal_t_anio",
        "excluidas_por_fuga": [
            "generacion_municipal_t_dia",
            "generacion_domiciliaria_urbana_t_anio",
            "generacion_domiciliaria_urbana_t_dia",
            "generacion_per_capita_municipal",
            "generacion_per_capita_domiciliaria",
        ],
        "derivadas": {
            "anio_desde_inicio": "anio menos el primer año observado",
            "particion_temporal": "entrenamiento 2019-2023 o prueba 2024",
            "brecha_poblacion": "poblacion_total - poblacion_urbana - poblacion_rural, solo si no hay diferencias",
            "log1p_poblacion_total_inei": "alternativa no sustitutiva para asimetría",
            "log1p_generacion_municipal_t_anio": "alternativa de transformación del objetivo",
        },
        "tratamiento": {
            "nulos": "reportar; no imputar automáticamente",
            "extremos": "reportar mediante IQR; no eliminar",
            "cobertura_incompleta": "conservar y filtrar posteriormente",
            "oeFA": "no incluido ni unido",
        },
    }
