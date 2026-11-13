from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.official_datasets import GeneracionResiduoDistritoAnual

MINAM_ANALYTIC_COLUMNS = (
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "anio",
    "poblacion_total_inei",
    "poblacion_urbana_inei",
    "poblacion_rural_inei",
    "generacion_municipal_t_anio",
)

MINAM_LEAKAGE_COLUMNS = (
    "generacion_municipal_t_dia",
    "generacion_domiciliaria_urbana_t_anio",
    "generacion_domiciliaria_urbana_t_dia",
    "generacion_per_capita_municipal",
    "generacion_per_capita_domiciliaria",
)


def seleccionar_minam(session: Session) -> list[dict[str, Any]]:
    """Obtiene únicamente las columnas necesarias para el dataset analítico."""
    dataset = GeneracionResiduoDistritoAnual
    consulta = (
        select(
            dataset.ubigeo,
            dataset.departamento,
            dataset.provincia,
            dataset.distrito,
            dataset.anio,
            dataset.poblacion_total_inei,
            dataset.poblacion_urbana_inei,
            dataset.poblacion_rural_inei,
            dataset.generacion_municipal_t_anio,
        )
        .order_by(dataset.ubigeo, dataset.anio)
    )
    return [dict(fila) for fila in session.execute(consulta).mappings()]
