"""Lectura segura de archivos tabulares recibidos temporalmente."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, BinaryIO, Iterable


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


class ETLFileError(ValueError):
    """Error controlado durante la inspección o lectura de un archivo."""


class UnsupportedFileTypeError(ETLFileError):
    """La extensión o el tipo MIME no está soportado."""


class FileSizeLimitError(ETLFileError):
    """El archivo excede el límite configurado."""


class EmptyFileError(ETLFileError):
    """El archivo no contiene encabezados ni filas."""


class FileEncodingError(ETLFileError):
    """El CSV no pudo decodificarse con la codificación admitida."""


class InvalidHeaderError(ETLFileError):
    """El encabezado está vacío o contiene columnas repetidas."""


class InvalidSpreadsheetError(ETLFileError):
    """El libro XLSX no pudo abrirse o tiene una estructura inválida."""


@dataclass(frozen=True)
class FilaArchivo:
    numero: int
    datos: dict[str, Any]


@dataclass(frozen=True)
class ArchivoTabular:
    nombre: str
    tipo: str
    columnas: tuple[str, ...]
    filas: tuple[FilaArchivo, ...]
    encabezados_originales: tuple[str, ...] = ()
    separador: str | None = None
    codificacion: str | None = None


def _validar_metadata_archivo(
    filename: str,
    content_type: str | None,
    size: int,
    max_size: int,
) -> str:
    extension = Path(filename).suffix.casefold()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            "Solo se admiten archivos .csv y .xlsx; .xls no está soportado."
        )
    if size > max_size:
        raise FileSizeLimitError(
            f"El archivo excede el límite de {max_size // (1024 * 1024)} MB."
        )

    tipos_permitidos = {
        ".csv": {"text/csv", "application/csv", "application/octet-stream"},
        ".xlsx": {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        },
    }
    if content_type and content_type.casefold() not in tipos_permitidos[extension]:
        raise UnsupportedFileTypeError(
            f"El tipo MIME {content_type!r} no corresponde a {extension}."
        )
    return extension


def _tamano_y_rebobinar(stream: BinaryIO) -> int:
    try:
        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        return size
    except (AttributeError, OSError) as error:
        raise ETLFileError("No se pudo inspeccionar el tamaño del archivo.") from error
    finally:
        try:
            stream.seek(0)
        except (AttributeError, OSError):
            pass


def _limpiar_encabezado(valor: Any) -> str:
    encabezado = str(valor).lstrip("\ufeff").strip()
    if len(encabezado) >= 2 and encabezado[0] == encabezado[-1] == '"':
        encabezado = encabezado[1:-1].strip()
    return encabezado


def _filas_desde_matriz(
    filas: Iterable[tuple[Any, ...]],
    *,
    separador: str | None = None,
    codificacion: str | None = None,
) -> ArchivoTabular:
    encabezados: tuple[str, ...] | None = None
    encabezados_originales: tuple[str, ...] | None = None
    resultado: list[FilaArchivo] = []

    for numero, valores in enumerate(filas, start=1):
        valores_originales = tuple(valores)
        valores_limpios = tuple(
            None if valor is None else str(valor).strip() if isinstance(valor, str) else valor
            for valor in valores
        )
        if encabezados is None:
            if not any(valor not in (None, "") for valor in valores_limpios):
                continue
            encabezados_originales = tuple(
                str(valor) if valor not in (None, "") else ""
                for valor in valores_originales
            )
            encabezados = tuple(
                _limpiar_encabezado(valor) if valor != "" else ""
                for valor in encabezados_originales
            )
            encabezados_normalizados = [valor.casefold() for valor in encabezados]
            if not encabezados or any(not valor for valor in encabezados):
                raise InvalidHeaderError("El archivo contiene encabezados vacíos.")
            if len(encabezados_normalizados) != len(set(encabezados_normalizados)):
                raise InvalidHeaderError("El archivo contiene columnas duplicadas.")
            continue

        if not any(valor not in (None, "") for valor in valores_limpios):
            continue
        if len(valores_limpios) > len(encabezados):
            raise ETLFileError(f"La fila {numero} tiene más valores que el encabezado.")
        datos = dict(zip(encabezados, valores_limpios, strict=False))
        datos.update({columna: None for columna in encabezados[len(valores_limpios) :]})
        resultado.append(FilaArchivo(numero=numero, datos=datos))

    if encabezados is None or not resultado:
        raise EmptyFileError("El archivo no contiene filas de datos.")
    return ArchivoTabular(
        nombre="",
        tipo="",
        columnas=encabezados,
        filas=tuple(resultado),
        encabezados_originales=encabezados_originales or encabezados,
        separador=separador,
        codificacion=codificacion,
    )


def _detectar_separador(texto: str) -> str:
    muestra = "\n".join(texto.splitlines()[:20])
    try:
        return csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
    except csv.Error:
        return ";"


def _decodificar_csv(contenido: bytes, encoding: str | None) -> tuple[str, str]:
    codificaciones = (encoding,) if encoding else ("utf-8-sig", "utf-8", "latin-1")
    for candidata in codificaciones:
        if candidata is None:
            continue
        try:
            return contenido.decode(candidata), candidata
        except (LookupError, UnicodeDecodeError):
            continue
    raise FileEncodingError(
        "No se pudo decodificar el CSV como UTF-8, UTF-8-SIG o Latin-1."
    )


def _leer_csv(
    contenido: bytes,
    *,
    delimiter: str | None = None,
    encoding: str | None = None,
) -> ArchivoTabular:
    texto, codificacion_usada = _decodificar_csv(contenido, encoding)
    separador = delimiter or _detectar_separador(texto)
    try:
        archivo = _filas_desde_matriz(
            tuple(tuple(fila) for fila in csv.reader(io.StringIO(texto), delimiter=separador)),
            separador=separador,
            codificacion=codificacion_usada,
        )
        if contenido.startswith(b"\xef\xbb\xbf") and archivo.encabezados_originales:
            originales = (
                "\ufeff" + archivo.encabezados_originales[0],
                *archivo.encabezados_originales[1:],
            )
            archivo = replace(archivo, encabezados_originales=originales)
        return archivo
    except csv.Error as error:
        raise ETLFileError("El CSV tiene una estructura inválida.") from error


def _leer_xlsx(contenido: bytes) -> ArchivoTabular:
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise ETLFileError("La dependencia openpyxl es necesaria para leer XLSX.") from error

    try:
        libro = load_workbook(
            io.BytesIO(contenido),
            read_only=True,
            data_only=True,
            keep_links=False,
        )
        try:
            hoja = libro.active
            return _filas_desde_matriz(hoja.iter_rows(values_only=True))
        finally:
            libro.close()
    except ETLFileError:
        raise
    except Exception as error:
        raise InvalidSpreadsheetError("No se pudo leer el libro XLSX.") from error


def leer_archivo(
    stream: BinaryIO,
    filename: str,
    content_type: str | None = None,
    max_size: int = MAX_FILE_SIZE_BYTES,
    delimiter: str | None = None,
    encoding: str | None = None,
) -> ArchivoTabular:
    """Lee un CSV o XLSX sin persistir el archivo en disco.

    ``data_only=True`` evita evaluar fórmulas y los archivos XLSM/XLS no se
    aceptan; esto excluye macros y formatos binarios no soportados.
    """

    size = _tamano_y_rebobinar(stream)
    extension = _validar_metadata_archivo(filename, content_type, size, max_size)
    contenido = stream.read()
    if not contenido:
        raise EmptyFileError("El archivo está vacío.")
    archivo = (
        _leer_csv(contenido, delimiter=delimiter, encoding=encoding)
        if extension == ".csv"
        else _leer_xlsx(contenido)
    )
    return ArchivoTabular(
        nombre=Path(filename).name,
        tipo=extension.removeprefix("."),
        columnas=archivo.columnas,
        filas=archivo.filas,
        encabezados_originales=archivo.encabezados_originales,
        separador=archivo.separador,
        codificacion=archivo.codificacion,
    )
