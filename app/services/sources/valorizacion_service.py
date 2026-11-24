"""Consultas descriptivas de valorización de residuos sólidos."""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parents[3]
GRUPO_B_DIR = BASE_DIR / "data" / "staging" / "grupo_b"

ARCHIVOS = {
    "organica": (
        GRUPO_B_DIR
        / "1.2 Dataset_Valorización de Residuos Sólidos Orgánicos a Nivel Distrital_2019-2024.xlsx",
        "QRESIDUOSVALORGAN",
        "Valorización orgánica",
    ),
    "inorganica": (
        GRUPO_B_DIR
        / "1.1 Dataset_Valorización de Residuos Sólidos Inorgánicos a Nivel Distrital 2019-2024.csv",
        "QRESIDUOSVALINORGAN",
        "Valorización inorgánica",
    ),
}


class ValorizacionServiceError(Exception):
    """Error al consultar los archivos de valorización."""


def _normalizar_columna(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _normalizar_ubigeo(value: Any) -> str:
    if value is None:
        return ""

    texto = str(value).strip()

    if texto.endswith(".0"):
        texto = texto[:-2]

    return texto.zfill(6)


def _numero(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None

    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError) as error:
        raise ValorizacionServiceError(
            f"Valor numérico inválido en valorización: {value}"
        ) from error


def _crear_registro(
    row: dict[str, Any],
    columna_valor: str,
    tipo: str,
    nombre: str,
) -> dict[str, Any] | None:
    datos = {
        _normalizar_columna(key): value
        for key, value in row.items()
    }

    ubigeo = _normalizar_ubigeo(datos.get("UBIGEO"))
    periodo = datos.get("PERIODO")

    if not ubigeo or not periodo:
        return None

    valor = _numero(datos.get(columna_valor))

    if valor is None:
        return None

    try:
        anio = int(float(str(periodo).strip()))
    except (TypeError, ValueError) as error:
        raise ValorizacionServiceError(
            f"Periodo inválido en valorización: {periodo}"
        ) from error

    return {
        "ubigeo": ubigeo,
        "departamento": str(datos.get("DEPARTAMENTO") or "").strip(),
        "provincia": str(datos.get("PROVINCIA") or "").strip(),
        "distrito": str(datos.get("DISTRITO") or "").strip(),
        "anio": anio,
        "valor": valor,
        "tipo": tipo,
        "fuente": nombre,
    }


@lru_cache(maxsize=2)
def _cargar_dataset(tipo: str) -> tuple[dict[str, Any], ...]:
    if tipo not in ARCHIVOS:
        raise ValorizacionServiceError(
            "Tipo desconocido. Utiliza 'organica' o 'inorganica'."
        )

    path, columna_valor, nombre = ARCHIVOS[tipo]

    if not path.is_file():
        raise ValorizacionServiceError(
            f"No se encontró el archivo de valorización: {path.name}"
        )

    registros = []

    try:
        if path.suffix.lower() == ".csv":
            with path.open(
                "r",
                encoding="cp1252",
                newline="",
            ) as archivo:
                reader = csv.DictReader(archivo, delimiter=";")

                if not reader.fieldnames:
                    raise ValorizacionServiceError(
                        f"El CSV no contiene encabezados: {path.name}"
                    )

                for row in reader:
                    registro = _crear_registro(
                        row, columna_valor, tipo, nombre
                    )
                    if registro is not None:
                        registros.append(registro)

        else:
            workbook = load_workbook(
                path,
                read_only=True,
                data_only=True,
            )

            try:
                sheet = workbook.active
                rows = sheet.iter_rows(values_only=True)
                headers = next(rows, None)

                if not headers:
                    raise ValorizacionServiceError(
                        f"El Excel no contiene encabezados: {path.name}"
                    )

                for values in rows:
                    row = dict(zip(headers, values))
                    registro = _crear_registro(
                        row, columna_valor, tipo, nombre
                    )
                    if registro is not None:
                        registros.append(registro)
            finally:
                workbook.close()

    except ValorizacionServiceError:
        raise
    except (OSError, csv.Error, ValueError, TypeError) as error:
        raise ValorizacionServiceError(
            f"No se pudo leer {path.name}: {error}"
        ) from error

    if not registros:
        raise ValorizacionServiceError(
            f"No se encontraron registros válidos en {path.name}."
        )

    return tuple(registros)


def consultar_valorizacion(
    *,
    tipo: str,
    anio: int | None = None,
    departamento: str | None = None,
    provincia: str | None = None,
    ubigeo: str | None = None,
) -> list[dict[str, Any]]:
    registros = list(_cargar_dataset(tipo))

    filtros = {
        "departamento": departamento,
        "provincia": provincia,
    }

    if anio is not None:
        registros = [
            row for row in registros if row["anio"] == anio
        ]

    if ubigeo:
        codigo = _normalizar_ubigeo(ubigeo)
        registros = [
            row for row in registros if row["ubigeo"] == codigo
        ]

    for campo, valor in filtros.items():
        if valor:
            registros = [
                row for row in registros
                if row[campo].casefold() == valor.strip().casefold()
            ]

    return sorted(
        registros,
        key=lambda row: (
            row["departamento"],
            row["provincia"],
            row["distrito"],
            row["anio"],
        ),
    )


def resumir_valorizacion(
    *,
    tipo: str,
    anio: int | None = None,
    departamento: str | None = None,
) -> dict[str, Any]:
    registros = consultar_valorizacion(
        tipo=tipo,
        anio=anio,
        departamento=departamento,
    )

    valores = [row["valor"] for row in registros]

    return {
        "tipo": tipo,
        "anio": anio,
        "departamento": departamento,
        "total_registros": len(registros),
        "total_valorizado": round(sum(valores), 2),
        "promedio": round(sum(valores) / len(valores), 2) if valores else 0,
        "distritos": len({row["ubigeo"] for row in registros}),
        "fuente": registros[0]["fuente"] if registros else None,
        "unidad": None,
        "nota": "La unidad de medida debe confirmarse con los metadatos de la fuente.",
    }


def limpiar_cache_valorizacion() -> None:
    _cargar_dataset.cache_clear()