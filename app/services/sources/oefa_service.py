
"""Consulta de solo lectura del inventario de áreas degradadas OEFA."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
ARCHIVO_OEFA = BASE_DIR / "data" / "raw" / "oefa_areas_degradadas.csv"


class OefaServiceError(Exception):
    """Error al consultar el inventario OEFA."""


COLUMNAS_NUMERICAS = {
    "este",
    "norte",
    "perimetro",
    "area_m2",
    "area_ha",
    "cantidad_municipalidades_disponen",
    "anio_incorporacion",
}


def _numero(valor: str | None, campo: str) -> int | float | None:
    if valor is None or not valor.strip():
        return None

    try:
        numero = float(valor.strip().replace(",", "."))
        if campo == "anio_incorporacion":
            return int(numero)
        return numero
    except (ValueError, TypeError):
        return None


def _normalizar_registro(fila: dict[str, str]) -> dict[str, Any]:
    registro = {
        clave.strip().lower(): (
            valor.strip() if valor and valor.strip() else None
        )
        for clave, valor in fila.items()
        if clave
    }

    for campo in COLUMNAS_NUMERICAS:
        registro[campo] = _numero(registro.get(campo), campo)

    return registro


@lru_cache(maxsize=1)
def listar_areas_oefa() -> tuple[dict[str, Any], ...]:
    if not ARCHIVO_OEFA.exists():
        raise OefaServiceError("No se encontró el archivo original de OEFA.")

    try:
        with ARCHIVO_OEFA.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as archivo:
            lector = csv.DictReader(archivo)
            registros = tuple(
                _normalizar_registro(fila)
                for fila in lector
            )

        if not registros:
            raise OefaServiceError("El inventario OEFA no contiene registros.")

        return registros

    except OefaServiceError:
        raise
    except Exception as error:
        raise OefaServiceError(
            f"No se pudo leer el inventario OEFA: {error}"
        ) from error


def consultar_areas_oefa(
    *,
    departamento: str | None = None,
    provincia: str | None = None,
    distrito: str | None = None,
    categoria: str | None = None,
    anio_incorporacion: int | None = None,
    id_uf: str | None = None,
) -> list[dict[str, Any]]:
    registros = list(listar_areas_oefa())

    filtros = {
        "departamento": departamento,
        "provincia": provincia,
        "distrito": distrito,
        "categoria": categoria,
        "id_uf": id_uf,
    }

    for campo, valor in filtros.items():
        if valor:
            buscado = valor.strip().casefold()
            registros = [
                registro
                for registro in registros
                if registro.get(campo)
                and buscado in registro[campo].casefold()
            ]

    if anio_incorporacion is not None:
        registros = [
            registro
            for registro in registros
            if registro["anio_incorporacion"] == anio_incorporacion
        ]

    return registros


def consultar_area_oefa(id_uf: str) -> list[dict[str, Any]]:
    return consultar_areas_oefa(id_uf=id_uf)


def resumir_areas_oefa() -> dict[str, Any]:
    registros = listar_areas_oefa()

    return {
        "total_registros": len(registros),
        "por_categoria": _contar(registros, "categoria"),
        "por_departamento": _contar(registros, "departamento"),
        "por_anio_incorporacion": _contar(
            registros,
            "anio_incorporacion",
        ),
        "con_ubigeo": sum(bool(r["ubigeo"]) for r in registros),
        "con_coordenadas": sum(
            r["este"] is not None and r["norte"] is not None
            for r in registros
        ),
        "con_area_ha": sum(r["area_ha"] is not None for r in registros),
        "fecha_corte": sorted({
            r["fecha_corte"]
            for r in registros
            if r["fecha_corte"]
        }),
        "fuente": ARCHIVO_OEFA.name,
        "nota": (
            "Los registros sin UBIGEO o coordenadas no se georreferencian "
            "automáticamente. La categoría se conserva según la fuente OEFA."
        ),
    }


def _contar(
    registros: tuple[dict[str, Any], ...],
    campo: str,
) -> dict[str, int]:
    resultado: dict[str, int] = {}

    for registro in registros:
        valor = registro.get(campo)
        etiqueta = str(valor) if valor is not None else "No especificado"
        resultado[etiqueta] = resultado.get(etiqueta, 0) + 1

    return dict(sorted(resultado.items()))


def limpiar_cache_oefa() -> None:
    listar_areas_oefa.cache_clear()
