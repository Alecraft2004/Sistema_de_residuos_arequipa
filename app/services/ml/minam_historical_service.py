
"""Consultas de generación municipal histórica desde el dataset MINAM."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
HISTORICAL_PATH = BASE_DIR / "data" / "processed" / "minam_features.csv"


class HistoricalServiceError(Exception):
    """Error controlado al consultar el histórico MINAM."""


def normalizar_ubigeo(value: Any) -> str:
    """Normaliza UBIGEO a seis dígitos."""
    return str(value or "").strip().zfill(6)


@lru_cache(maxsize=1)
def _cargar_historico() -> tuple[dict[str, Any], ...]:
    if not HISTORICAL_PATH.is_file():
        raise HistoricalServiceError(
            "No se encontró el archivo histórico MINAM."
        )

    try:
        with HISTORICAL_PATH.open(
            encoding="utf-8-sig",
            newline="",
        ) as source:
            reader = csv.DictReader(source)

            required = {
                "ubigeo",
                "departamento",
                "provincia",
                "distrito",
                "anio_objetivo",
                "generacion_municipal_t_anio",
                "particion_temporal",
            }

            if not required.issubset(set(reader.fieldnames or [])):
                raise HistoricalServiceError(
                    "El CSV MINAM no contiene todas las columnas requeridas."
                )

            rows = []

            for row in reader:
                if not row.get("generacion_municipal_t_anio"):
                    continue

                rows.append({
                    "ubigeo": normalizar_ubigeo(row["ubigeo"]),
                    "departamento": row["departamento"].strip(),
                    "provincia": row["provincia"].strip(),
                    "distrito": row["distrito"].strip(),
                    "anio": int(row["anio_objetivo"]),
                    "generacion_real": float(
                        row["generacion_municipal_t_anio"]
                    ),
                    "particion_temporal": row["particion_temporal"].strip(),
                    "unidad": "toneladas/año",
                    "fuente": "MINAM",
                })

    except HistoricalServiceError:
        raise
    except (OSError, ValueError, TypeError, csv.Error) as error:
        raise HistoricalServiceError(
            "No se pudo procesar el histórico MINAM."
        ) from error

    if not rows:
        raise HistoricalServiceError("El histórico MINAM está vacío.")

    keys = [(row["ubigeo"], row["anio"]) for row in rows]

    if len(keys) != len(set(keys)):
        raise HistoricalServiceError(
            "Se detectaron registros duplicados por UBIGEO y año."
        )

    return tuple(rows)


def listar_historico(
    *,
    anio: int | None = None,
    ubigeo: str | None = None,
    departamento: str | None = None,
    provincia: str | None = None,
    distrito: str | None = None,
) -> list[dict[str, Any]]:
    rows = list(_cargar_historico())

    filters = {
        "ubigeo": normalizar_ubigeo(ubigeo) if ubigeo else None,
        "departamento": departamento,
        "provincia": provincia,
        "distrito": distrito,
    }

    if anio is not None:
        rows = [row for row in rows if row["anio"] == anio]

    for field, value in filters.items():
        if value is not None:
            rows = [
                row for row in rows
                if str(row[field]).casefold() == value.strip().casefold()
            ]

    return sorted(
        rows,
        key=lambda row: (row["departamento"], row["provincia"],
                         row["distrito"], row["anio"]),
    )


def limpiar_cache_historico() -> None:
    """Permite recargar el CSV después de actualizar el dataset."""
    _cargar_historico.cache_clear()
