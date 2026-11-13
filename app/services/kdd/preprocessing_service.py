from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

MINAM_NUMERIC_COLUMNS = (
    "poblacion_total_inei",
    "poblacion_urbana_inei",
    "poblacion_rural_inei",
    "generacion_municipal_t_anio",
)

MINAM_REQUIRED_COLUMNS = (
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "anio",
    *MINAM_NUMERIC_COLUMNS,
)


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _decimal(value: Any) -> Decimal | None:
    if _missing(value):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _percentile(values: list[Decimal], percentile: float) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = Decimal(str(position - lower))
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _outlier_summary(values: Iterable[Any]) -> dict[str, Any]:
    numeric = [value for value in (_decimal(item) for item in values) if value is not None]
    if not numeric:
        return {"cantidad": 0, "limite_inferior": None, "limite_superior": None}
    q1 = _percentile(numeric, 0.25)
    q3 = _percentile(numeric, 0.75)
    iqr = q3 - q1
    lower = q1 - Decimal("1.5") * iqr
    upper = q3 + Decimal("1.5") * iqr
    return {
        "cantidad": sum(value < lower or value > upper for value in numeric),
        "limite_inferior": str(lower),
        "limite_superior": str(upper),
        "metodo": "IQR_1.5",
        "tratamiento": "documentado_sin_eliminacion",
    }


def evaluar_calidad_minam(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Evalúa calidad sin eliminar ni corregir registros."""
    missing = {
        column: sum(_missing(record.get(column)) for record in records)
        for column in MINAM_REQUIRED_COLUMNS
    }
    negative = {
        column: sum(
            (value := _decimal(record.get(column))) is not None and value < 0
            for record in records
        )
        for column in MINAM_NUMERIC_COLUMNS
    }
    keys = [
        (record.get("ubigeo"), record.get("anio"))
        for record in records
        if not _missing(record.get("ubigeo")) and not _missing(record.get("anio"))
    ]
    key_counts = Counter(keys)
    duplicate_groups = {
        f"{ubigeo}|{anio}": count
        for (ubigeo, anio), count in key_counts.items()
        if count > 1
    }
    type_observations = {
        column: sorted(
            {type(record.get(column)).__name__ for record in records if record.get(column) is not None}
        )
        for column in MINAM_REQUIRED_COLUMNS
    }

    population_mismatches = 0
    population_differences: list[Decimal] = []
    for record in records:
        total = _decimal(record.get("poblacion_total_inei"))
        urban = _decimal(record.get("poblacion_urbana_inei"))
        rural = _decimal(record.get("poblacion_rural_inei"))
        if total is not None and urban is not None and rural is not None:
            difference = total - urban - rural
            population_differences.append(abs(difference))
            population_mismatches += difference != 0

    coverage = Counter(
        len(
            {
                record.get("anio")
                for record in records
                if record.get("ubigeo") == ubigeo
            }
        )
        for ubigeo in {record.get("ubigeo") for record in records}
    )
    years = sorted(
        {
            int(record["anio"])
            for record in records
            if not _missing(record.get("anio"))
        }
    )
    return {
        "dataset": "MINAM_GENERACION_ANUAL",
        "filas_antes": len(records),
        "filas_despues": len(records),
        "filas_excluidas": 0,
        "columnas_obligatorias": list(MINAM_REQUIRED_COLUMNS),
        "valores_faltantes": missing,
        "valores_negativos": negative,
        "duplicados_por_ubigeo_anio": {
            "grupos": duplicate_groups,
            "filas_excedentes": sum(count - 1 for count in duplicate_groups.values()),
        },
        "tipos_observados": type_observations,
        "consistencia_poblacion": {
            "filas_comparables": len(population_differences),
            "filas_con_diferencia": population_mismatches,
            "diferencia_maxima": str(max(population_differences, default=Decimal("0"))),
            "brecha_permitida": population_mismatches == 0,
        },
        "cobertura_temporal": {
            "anios": years,
            "por_ubigeo": dict(sorted(coverage.items())),
            "ubigeos_con_seis_anios": coverage.get(6, 0),
            "anios_minimos_por_ubigeo": min(coverage, default=0),
            "anios_maximos_por_ubigeo": max(coverage, default=0),
        },
        "valores_extremos": {
            column: _outlier_summary(record.get(column) for record in records)
            for column in MINAM_NUMERIC_COLUMNS
        },
        "reglas": {
            "no_eliminar_extremos": True,
            "no_eliminar_cobertura_incompleta": True,
            "clave_unica_esperada": ["ubigeo", "anio"],
            "particion_temporal": {"entrenamiento": [2019, 2023], "prueba": [2024]},
        },
    }


def validar_particion_temporal(year: Any) -> str:
    """Clasifica años sin permitir que el año de prueba entre al entrenamiento."""
    numeric_year = int(year)
    if 2019 <= numeric_year <= 2023:
        return "entrenamiento"
    if numeric_year == 2024:
        return "prueba"
    return "fuera_de_periodo"

