
"""Lectura de rutas del programa Arequipa Recicla 2026."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parents[3]
CARPETA = BASE_DIR / "data" / "staging" / "grupo_b"

ARCHIVO_RUTAS = (
    CARPETA
    / "RUTAS PROGRAMA AREQUIPA RECICLA ENERO A JUNIO DEL 2026 - MPA VRSIM.xlsx"
)

ARCHIVO_DICCIONARIO = (
    CARPETA
    / "Diccionario de Rutas de Recoleccion Selectiva de Residuos Inorganicos del Programa Arequipa Recicla 2026 -MPA.xlsx"
)


class RutasServiceError(Exception):
    """Error al consultar los archivos de rutas."""


def _normalizar_codigo(codigo: Any) -> str | None:
    if codigo is None:
        return None

    return "".join(str(codigo).upper().split())


@lru_cache(maxsize=1)
def listar_rutas() -> tuple[dict[str, Any], ...]:
    if not ARCHIVO_RUTAS.exists():
        raise RutasServiceError("No se encontró el archivo de rutas.")

    try:
        wb = load_workbook(
            ARCHIVO_RUTAS,
            read_only=True,
            data_only=True,
        )
        ws = wb["Lista"]

        registros = []

        for fila in ws.iter_rows(min_row=2, values_only=True):
            numero, ruta, descripcion, dia, frecuencia, turno, hora = fila[:7]

            if not ruta:
                continue

            registros.append({
                "numero": numero,
                "codigo": _normalizar_codigo(ruta),
                "descripcion": str(descripcion).strip() if descripcion else None,
                "dia": str(dia).strip() if dia else None,
                "frecuencia": str(frecuencia).strip() if frecuencia else None,
                "turno": str(turno).strip() if turno else None,
                "hora": str(hora).strip() if hora else None,
                "fuente": ARCHIVO_RUTAS.name,
            })

        wb.close()

        if not registros:
            raise RutasServiceError("El archivo no contiene rutas válidas.")

        return tuple(registros)

    except RutasServiceError:
        raise
    except Exception as error:
        raise RutasServiceError(
            f"No se pudo leer el archivo de rutas: {error}"
        ) from error


@lru_cache(maxsize=1)
def obtener_diccionario() -> tuple[dict[str, Any], ...]:
    if not ARCHIVO_DICCIONARIO.exists():
        raise RutasServiceError("No se encontró el diccionario de rutas.")

    try:
        wb = load_workbook(
            ARCHIVO_DICCIONARIO,
            read_only=True,
            data_only=True,
        )
        ws = wb["Diccionario"]

        registros = []

        for fila in ws.iter_rows(min_row=2, values_only=True):
            variable, descripcion, tipo, tamano, adicional = fila[:5]

            if not descripcion:
                continue

            registros.append({
                "variable": str(variable).strip() if variable else "DESCRIPCION",
                "descripcion": str(descripcion).strip(),
                "tipo_dato": tipo,
                "tamano": tamano,
                "informacion_adicional": (
                    str(adicional).strip() if adicional else None
                ),
            })

        wb.close()
        return tuple(registros)

    except Exception as error:
        raise RutasServiceError(
            f"No se pudo leer el diccionario: {error}"
        ) from error


def consultar_rutas(
    *,
    dia: str | None = None,
    frecuencia: str | None = None,
    turno: str | None = None,
) -> list[dict[str, Any]]:
    registros = list(listar_rutas())

    filtros = {
        "dia": dia,
        "frecuencia": frecuencia,
        "turno": turno,
    }

    for campo, valor in filtros.items():
        if valor:
            registros = [
                registro
                for registro in registros
                if registro[campo]
                and valor.strip().casefold() in registro[campo].casefold()
            ]

    return registros


def consultar_ruta(codigo: str) -> dict[str, Any] | None:
    codigo_normalizado = _normalizar_codigo(codigo)

    return next(
        (
            ruta
            for ruta in listar_rutas()
            if ruta["codigo"] == codigo_normalizado
        ),
        None,
    )


def resumir_rutas() -> dict[str, Any]:
    registros = listar_rutas()

    return {
        "total_rutas": len(registros),
        "por_dia": _contar_valores(registros, "dia"),
        "por_frecuencia": _contar_valores(registros, "frecuencia"),
        "por_turno": _contar_valores(registros, "turno"),
        "rutas_con_datos_incompletos": sum(
            any(
                ruta[campo] is None
                for campo in ("dia", "frecuencia", "turno", "hora")
            )
            for ruta in registros
        ),
        "fuente": ARCHIVO_RUTAS.name,
    }


def _contar_valores(
    registros: tuple[dict[str, Any], ...],
    campo: str,
) -> dict[str, int]:
    resultado = {}

    for registro in registros:
        valor = registro[campo] or "No especificado"
        resultado[valor] = resultado.get(valor, 0) + 1

    return resultado


def limpiar_cache_rutas() -> None:
    listar_rutas.cache_clear()
    obtener_diccionario.cache_clear()
