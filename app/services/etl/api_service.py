"""Casos de uso transaccionales y consultas del API ETL."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .loading_service import actualizar_importacion, crear_importacion, registrar_rechazos
from .source_profiles import PerfilFuenteETL, obtener_perfil
from .transformation_service import transformar_fila
from .validation_service import ResultadoValidacionETL

BATCH_SIZE = 500


class DuplicateImportError(RuntimeError):
    """El archivo ya fue importado para el perfil solicitado."""


def _es_conflicto_hash(error: IntegrityError) -> bool:
    constraint_name = getattr(error.orig, "constraint_name", None)
    return (
        constraint_name == "uq_importaciones_etl_hash_perfil"
        or "uq_importaciones_etl_hash_perfil" in str(error)
    )


def _json_compatible(valor: Any) -> Any:
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {str(clave): _json_compatible(dato) for clave, dato in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_compatible(dato) for dato in valor]
    return valor


def _modelos():
    from ...models.etl import ImportacionETL, RegistroRechazadoETL
    from ...models.official_datasets import AreaDegradadaOEFA, GeneracionResiduoDistritoAnual

    return (
        ImportacionETL,
        RegistroRechazadoETL,
        GeneracionResiduoDistritoAnual,
        AreaDegradadaOEFA,
    )


def _datos_destino(
    perfil: PerfilFuenteETL,
    datos: dict[str, Any],
    importacion_id: int,
    datos_originales: dict[str, Any],
) -> Any:
    _, _, GeneracionResiduoDistritoAnual, AreaDegradadaOEFA = _modelos()
    comunes = {
        "importacion_id": importacion_id,
        "perfil_fuente": perfil.identificador,
        "datos_originales": _json_compatible(datos_originales),
    }
    if perfil.identificador == "MINAM_GENERACION_ANUAL":
        campos = {
            "ubigeo",
            "anio",
            "departamento",
            "provincia",
            "distrito",
            "poblacion_total_inei",
            "poblacion_urbana_inei",
            "poblacion_rural_inei",
            "generacion_per_capita_domiciliaria",
            "generacion_domiciliaria_urbana_t_dia",
            "generacion_domiciliaria_urbana_t_anio",
            "generacion_municipal_t_anio",
            "generacion_municipal_t_dia",
            "generacion_per_capita_municipal",
        }
        return GeneracionResiduoDistritoAnual(
            **comunes,
            **{campo: datos.get(campo) for campo in campos},
        )
    if perfil.identificador == "OEFA_AREAS_DEGRADADAS":
        mapeo = {
            "municipalidad_administra": "municipalidad_administradora",
        }
        campos = {
            "ubigeo",
            "id_uf",
            "denominacion",
            "zona",
            "este",
            "norte",
            "perimetro",
            "area_m2",
            "area_ha",
            "municipalidad_disponen",
            "cantidad_municipalidades_disponen",
            "segregacion",
            "crianza_animal",
            "quema_rrss",
            "rrss_salud",
            "rrss_industrial",
            "natural_aguajal",
            "natural_bofedal",
            "natural_pantano",
            "amortiguamiento_anp",
            "anp",
            "categoria",
            "anio_incorporacion",
            "fecha_corte",
        }
        valores = {
            mapeo.get(campo, campo): datos.get(campo)
            for campo in campos
        }
        return AreaDegradadaOEFA(**comunes, **valores)
    raise ValueError(f"El perfil {perfil.identificador} no tiene destino configurado.")


def transformar_validos(
    perfil: PerfilFuenteETL,
    resultado: ResultadoValidacionETL,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        transformar_fila(fila, perfil.configuracion())
        for fila in resultado.filas_validas
    )


def importar_archivo(
    session: Session,
    *,
    archivo: Any,
    perfil_id: str,
    usuario_nombre: str,
    hash_archivo: str,
) -> Any:
    """Persiste una importación completa en una sola sesión y transacción."""

    perfil = obtener_perfil(perfil_id)
    resultado: ResultadoValidacionETL = archivo["resultado"]
    transformados = archivo["transformados"]
    _, _, _, _ = _modelos()
    from ...database import Usuario

    usuario_id: int | None = None

    try:
        with session.begin():
            usuario_id = session.scalar(
                select(Usuario.id).where(Usuario.usuario == usuario_nombre)
            )
            ImportacionETL, _, _, _ = _modelos()
            existente = session.scalar(
                select(ImportacionETL).where(
                    ImportacionETL.hash_archivo == hash_archivo,
                    ImportacionETL.perfil_fuente == perfil.identificador,
                )
            )
            if existente is not None:
                raise DuplicateImportError(
                    f"El archivo ya fue importado para {perfil.identificador} "
                    f"en la importación {existente.id}."
                )
            importacion = crear_importacion(
                session,
                nombre_archivo=archivo["nombre"],
                tipo_archivo=archivo["tipo"],
                perfil_fuente=perfil.identificador,
                entidad_fuente=perfil.entidad,
                hash_archivo=hash_archivo,
                usuario_id=usuario_id,
            )
            importacion.estado = "procesando"
            registrar_rechazos(
                session,
                importacion.id,
                [
                    (
                        rechazo.numero_fila,
                        _json_compatible(rechazo.datos_originales),
                        rechazo.motivo,
                    )
                    for rechazo in resultado.filas_rechazadas
                ],
            )
            for inicio in range(0, len(transformados), BATCH_SIZE):
                lote = transformados[inicio : inicio + BATCH_SIZE]
                session.add_all(
                    _datos_destino(
                        perfil,
                        fila["datos"],
                        importacion.id,
                        fila["datos_originales"],
                    )
                    for fila in lote
                )
                session.flush()
            actualizar_importacion(
                importacion,
                total_procesadas=len(archivo["filas"]),
                total_validas=len(transformados),
                total_rechazadas=len(resultado.filas_rechazadas),
                estado="completado",
            )
        return importacion
    except SQLAlchemyError as error:
        session.rollback()
        if isinstance(error, IntegrityError) and _es_conflicto_hash(error):
            ImportacionETL, _, _, _ = _modelos()
            existente = session.scalar(
                select(ImportacionETL).where(
                    ImportacionETL.hash_archivo == hash_archivo,
                    ImportacionETL.perfil_fuente == perfil.identificador,
                )
            )
            session.rollback()
            if existente is not None:
                raise DuplicateImportError(
                    f"El archivo ya fue importado para {perfil.identificador} "
                    f"en la importación {existente.id}."
                ) from error
        try:
            with session.begin():
                fallida = crear_importacion(
                    session,
                    nombre_archivo=archivo["nombre"],
                    tipo_archivo=archivo["tipo"],
                    perfil_fuente=perfil.identificador,
                    entidad_fuente=perfil.entidad,
                    hash_archivo=hash_archivo,
                    usuario_id=usuario_id,
                )
                actualizar_importacion(
                    fallida,
                    total_procesadas=len(archivo["filas"]),
                    total_validas=0,
                    total_rechazadas=0,
                    estado="fallido",
                    mensaje_error="La carga transaccional fue revertida.",
                )
        except SQLAlchemyError as audit_error:
            session.rollback()
            raise RuntimeError("No se pudo registrar el fallo de importación.") from audit_error
        raise RuntimeError("La carga fue revertida por un error de base de datos.") from error


def listar_importaciones(session: Session, offset: int, limit: int) -> tuple[list[Any], int]:
    ImportacionETL, _, _, _ = _modelos()
    total = session.scalar(select(func.count()).select_from(ImportacionETL)) or 0
    filas = list(
        session.scalars(
            select(ImportacionETL)
            .order_by(ImportacionETL.fecha_importacion.desc(), ImportacionETL.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return filas, total


def obtener_importacion(session: Session, importacion_id: int) -> Any | None:
    ImportacionETL, _, _, _ = _modelos()
    return session.get(ImportacionETL, importacion_id)


def listar_rechazados(
    session: Session, importacion_id: int, offset: int, limit: int
) -> tuple[list[Any], int]:
    _, RegistroRechazadoETL, _, _ = _modelos()
    consulta = select(RegistroRechazadoETL).where(
        RegistroRechazadoETL.importacion_id == importacion_id
    )
    total = session.scalar(
        select(func.count()).select_from(consulta.subquery())
    ) or 0
    filas = list(
        session.scalars(
            consulta.order_by(RegistroRechazadoETL.numero_fila)
            .offset(offset)
            .limit(limit)
        )
    )
    return filas, total


def obtener_estadisticas(session: Session) -> dict[str, int]:
    ImportacionETL, RegistroRechazadoETL, _, _ = _modelos()
    total = session.scalar(select(func.count()).select_from(ImportacionETL)) or 0
    completadas = session.scalar(
        select(func.count())
        .select_from(ImportacionETL)
        .where(ImportacionETL.estado == "completado")
    ) or 0
    fallidas = session.scalar(
        select(func.count()).select_from(ImportacionETL).where(
            ImportacionETL.estado == "fallido"
        )
    ) or 0
    def validos_por_perfil(perfil_fuente: str) -> int:
        return int(
            session.scalar(
                select(func.coalesce(func.sum(ImportacionETL.total_filas_validas), 0))
                .select_from(ImportacionETL)
                .where(
                    ImportacionETL.estado == "completado",
                    ImportacionETL.perfil_fuente == perfil_fuente,
                )
            )
            or 0
        )
    return {
        "total_importaciones": int(total),
        "importaciones_completadas": int(completadas),
        "importaciones_fallidas": int(fallidas),
        "registros_importados_minam": validos_por_perfil("MINAM_GENERACION_ANUAL"),
        "registros_importados_oefa": validos_por_perfil("OEFA_AREAS_DEGRADADAS"),
        "registros_rechazados": int(session.scalar(
            select(func.count()).select_from(RegistroRechazadoETL)
        ) or 0),
    }
