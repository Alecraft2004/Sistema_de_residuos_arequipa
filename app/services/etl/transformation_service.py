"""Transformaciones explícitas y reversibles para filas ETL."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from ...schemas.etl import ConfiguracionColumnasETL
from .ingestion_service import ArchivoTabular, FilaArchivo
from .validation_service import _parsear_fecha_compacta

_VALOR_CON_UNIDAD = re.compile(r"^\s*([-+]?\d+(?:[.,]\d+)?)\s*([^\d\s]+)\s*$")


def _normalizar_categoria(valor: Any, mapeo: dict[str, str]) -> Any:
    if not isinstance(valor, str):
        return valor
    limpio = " ".join(valor.strip().split())
    return mapeo.get(limpio.casefold(), limpio)


def _convertir_unidad(valor: Any, conversiones: dict[str, float]) -> Any:
    if not isinstance(valor, str):
        return valor
    coincidencia = _VALOR_CON_UNIDAD.match(valor)
    if not coincidencia:
        return valor
    cantidad = float(coincidencia.group(1).replace(",", "."))
    unidad = coincidencia.group(2).casefold()
    if unidad not in conversiones:
        raise ValueError(f"No existe equivalencia configurada para la unidad {unidad}.")
    resultado = cantidad * conversiones[unidad]
    return int(resultado) if resultado.is_integer() else resultado


def _convertir_tipo(valor: Any, tipo: str) -> Any:
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    if not isinstance(valor, str):
        return valor
    limpio = valor.strip()
    if tipo == "integer":
        return int(limpio)
    if tipo == "number":
        resultado = float(limpio.replace(",", "."))
        return int(resultado) if resultado.is_integer() else resultado
    if tipo == "boolean":
        normalizado = limpio.casefold()
        if normalizado in {"no precisa", "no precisado", "no especificado"}:
            return None
        if normalizado in {"si", "sí", "true", "1"}:
            return True
        if normalizado in {"no", "false", "0"}:
            return False
    if tipo == "date":
        if len(limpio) == 8 and limpio.isdigit():
            fecha_compacta = _parsear_fecha_compacta(limpio)
            if fecha_compacta is None:
                raise ValueError(f"Fecha compacta ambigua o inválida: {limpio}.")
            return fecha_compacta
        for formato in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(limpio, formato).date()
            except ValueError:
                continue
        return date.fromisoformat(limpio)
    return limpio


def transformar_fila(
    fila: FilaArchivo,
    configuracion: ConfiguracionColumnasETL,
) -> dict[str, Any]:
    """Mapea columnas y aplica solo normalizaciones declaradas."""

    transformada: dict[str, Any] = {}
    for origen, valor in fila.datos.items():
        destino = configuracion.mapeo_columnas.get(origen, origen)
        if destino in configuracion.tipos:
            valor = _convertir_tipo(valor, configuracion.tipos[destino])
        if destino in configuracion.categorias:
            valor = _normalizar_categoria(valor, configuracion.categorias[destino])
        if destino in configuracion.conversiones_unidad:
            valor = _convertir_unidad(valor, configuracion.conversiones_unidad[destino])
        transformada[destino] = valor
    return {
        "numero_fila": fila.numero,
        "perfil_fuente": configuracion.perfil_id,
        "fuente": configuracion.fuente,
        "datos": transformada,
        "datos_originales": dict(fila.datos),
    }


def transformar_archivo(
    archivo: ArchivoTabular,
    configuracion: ConfiguracionColumnasETL,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        transformar_fila(fila, configuracion)
        for fila in archivo.filas
    )
