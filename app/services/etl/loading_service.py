"""Persistencia explícita de auditoría ETL usando sesiones existentes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from ...models.etl import ImportacionETL


def crear_importacion(
    session: Session,
    *,
    nombre_archivo: str,
    tipo_archivo: str,
    perfil_fuente: str | None = None,
    entidad_fuente: str | None = None,
    hash_archivo: str | None = None,
    usuario_id: int | None = None,
) -> "ImportacionETL":
    from ...models.etl import ImportacionETL

    registro = ImportacionETL(
        nombre_archivo=nombre_archivo,
        tipo_archivo=tipo_archivo,
        perfil_fuente=perfil_fuente,
        entidad_fuente=entidad_fuente,
        hash_archivo=hash_archivo,
        usuario_id=usuario_id,
        estado="pendiente",
    )
    session.add(registro)
    session.flush()
    return registro


def actualizar_importacion(
    registro: ImportacionETL,
    *,
    total_procesadas: int,
    total_validas: int,
    total_rechazadas: int,
    estado: str,
    mensaje_error: str | None = None,
) -> "ImportacionETL":
    registro.total_filas_procesadas = total_procesadas
    registro.total_filas_validas = total_validas
    registro.total_filas_rechazadas = total_rechazadas
    registro.estado = estado
    registro.mensaje_error = mensaje_error
    return registro


def registrar_rechazos(
    session: Session,
    importacion_id: int,
    rechazos: list[tuple[int, dict[str, Any], str]],
) -> None:
    from ...models.etl import RegistroRechazadoETL

    session.add_all(
        RegistroRechazadoETL(
            importacion_id=importacion_id,
            numero_fila=numero_fila,
            datos_originales=datos,
            motivo_rechazo=motivo,
        )
        for numero_fila, datos, motivo in rechazos
    )
