"""Validación configurable de filas ETL sin imponer un contrato de negocio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ...schemas.etl import ConfiguracionColumnasETL
from .ingestion_service import ArchivoTabular, FilaArchivo


@dataclass(frozen=True)
class RechazoETL:
    numero_fila: int
    datos_originales: dict[str, Any]
    motivo: str


@dataclass(frozen=True)
class ResultadoValidacionETL:
    filas_validas: tuple[FilaArchivo, ...]
    filas_rechazadas: tuple[RechazoETL, ...]
    columnas_no_reconocidas: tuple[str, ...]
    columnas_faltantes: tuple[str, ...] = ()


def _valor_canonico(fila: FilaArchivo, configuracion: ConfiguracionColumnasETL, nombre: str) -> Any:
    for fuente, destino in configuracion.mapeo_columnas.items():
        if destino == nombre:
            return fila.datos.get(fuente)
    return fila.datos.get(nombre)


def _esta_vacio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _es_fecha_valida(valor: Any) -> bool:
    if isinstance(valor, (date, datetime)):
        return True
    if not isinstance(valor, str) or not valor.strip():
        return False
    texto = valor.strip()
    if len(texto) == 8 and texto.isdigit():
        return _parsear_fecha_compacta(texto) is not None
    formatos = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y")
    return any(
        _intentar_fecha(texto, formato)
        for formato in formatos
    ) or _intentar_datetime(texto)


def _intentar_fecha(texto: str, formato: str) -> bool:
    try:
        datetime.strptime(texto, formato)
        return True
    except ValueError:
        return False


def _parsear_fecha_compacta(texto: str) -> date | None:
        candidatos: list[date] = []
        for formato in ("%d%m%Y", "%Y%m%d"):
            try:
                candidata = datetime.strptime(texto, formato).date()
            except ValueError:
                continue
            if 1900 <= candidata.year <= 2100:
                candidatos.append(candidata)
        unicos = set(candidatos)
        if len(unicos) == 1:
            return candidatos[0]
        return None


def _intentar_datetime(texto: str) -> bool:
    try:
        datetime.fromisoformat(texto)
        return True
    except ValueError:
        return False


def _es_tipo_valido(valor: Any, tipo: str) -> bool:
    if tipo == "string":
        return isinstance(valor, str)
    if tipo == "integer":
        if isinstance(valor, int) and not isinstance(valor, bool):
            return True
        if isinstance(valor, str):
            try:
                return str(int(valor.strip())) == valor.strip()
            except ValueError:
                return False
        return False
    if tipo == "number":
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return True
        if isinstance(valor, str):
            try:
                float(valor.strip().replace(",", "."))
                return True
            except ValueError:
                return False
        return False
    if tipo == "date":
        return _es_fecha_valida(valor)
    if tipo == "boolean":
        return (
            isinstance(valor, bool)
            or (
                isinstance(valor, str)
                and valor.strip().casefold()
                in {"si", "sí", "no", "true", "false", "1", "0", "no precisa"}
            )
        )
    return False


def _es_negativo(valor: Any) -> bool:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return valor < 0
    if isinstance(valor, str):
        try:
            return float(valor.strip().replace(",", ".")) < 0
        except ValueError:
            return False
    return False


def _anio(valor: Any) -> int | None:
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        try:
            return int(valor.strip())
        except ValueError:
            return None
    return None


def validar_archivo(
    archivo: ArchivoTabular,
    configuracion: ConfiguracionColumnasETL,
) -> ResultadoValidacionETL:
    """Valida filas según reglas explícitas suministradas por la fuente."""

    columnas_mapeadas = set(configuracion.mapeo_columnas)
    columnas_no_reconocidas = tuple(
        columna for columna in archivo.columnas if columna not in columnas_mapeadas
    )
    fuentes_por_canonico = {
        destino: fuente
        for fuente, destino in configuracion.mapeo_columnas.items()
    }
    faltantes = []
    for columna in configuracion.columnas_obligatorias:
        fuente = fuentes_por_canonico.get(columna, columna)
        if fuente not in archivo.columnas:
            faltantes.append(columna)

    validas: list[FilaArchivo] = []
    rechazadas: list[RechazoETL] = []
    claves_vistas: set[tuple[Any, ...]] = set()

    for fila in archivo.filas:
        motivos: list[str] = []
        if faltantes:
            motivos.extend(f"Falta la columna obligatoria: {columna}." for columna in faltantes)

        for columna in configuracion.columnas_obligatorias:
            if _esta_vacio(_valor_canonico(fila, configuracion, columna)):
                motivos.append(f"El campo obligatorio {columna} está vacío.")

        for columna in configuracion.columnas_no_negativas:
            valor = _valor_canonico(fila, configuracion, columna)
            if _es_negativo(valor):
                motivos.append(f"El campo {columna} no puede ser negativo.")

        for columna in configuracion.columnas_fecha:
            valor = _valor_canonico(fila, configuracion, columna)
            if not _esta_vacio(valor) and not _es_fecha_valida(valor):
                motivos.append(f"La fecha de {columna} no es válida.")

        for columna, tipo in configuracion.tipos.items():
            valor = _valor_canonico(fila, configuracion, columna)
            if not _esta_vacio(valor) and not _es_tipo_valido(valor, tipo):
                motivos.append(f"El campo {columna} no cumple el tipo {tipo}.")

        if "anio" in configuracion.tipos:
            valor_anio = _anio(_valor_canonico(fila, configuracion, "anio"))
            if valor_anio is not None and configuracion.anio_desde is not None:
                limite_superior = configuracion.anio_hasta
                fuera_de_rango = valor_anio < configuracion.anio_desde
                if (
                    limite_superior is not None
                    and not configuracion.permitir_anios_futuros
                    and valor_anio > limite_superior
                ):
                    fuera_de_rango = True
                if fuera_de_rango:
                    motivos.append(f"El año {valor_anio} está fuera del rango permitido.")

        if configuracion.claves_duplicado:
            clave = tuple(
                _valor_canonico(fila, configuracion, columna)
                for columna in configuracion.claves_duplicado
            )
            if not any(_esta_vacio(valor) for valor in clave):
                if clave in claves_vistas:
                    motivos.append("Registro duplicado según la clave configurada.")
                else:
                    claves_vistas.add(clave)

        if motivos:
            rechazadas.append(
                RechazoETL(fila.numero, fila.datos, " ".join(motivos))
            )
        else:
            validas.append(fila)

    return ResultadoValidacionETL(
        filas_validas=tuple(validas),
        filas_rechazadas=tuple(rechazadas),
        columnas_no_reconocidas=columnas_no_reconocidas,
        columnas_faltantes=tuple(faltantes),
    )
