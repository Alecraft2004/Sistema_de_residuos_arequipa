"""Endpoints autenticados para validación e importación ETL."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Generator
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..database import get_engine
from ..schemas.etl_api import (
    EstadisticasETLResponse,
    ImportacionDetalleResponse,
    ImportacionesPageResponse,
    ImportacionResumenResponse,
    RechazadosPageResponse,
    RechazoETLResponse,
    VistaPreviaETLResponse,
)
from ..services.etl.api_service import (
    DuplicateImportError,
    importar_archivo,
    listar_importaciones,
    listar_rechazados,
    obtener_estadisticas,
    obtener_importacion,
    transformar_validos,
)
from ..services.etl.ingestion_service import ETLFileError, leer_archivo
from ..services.etl.source_profiles import obtener_perfil
from ..services.etl.validation_service import validar_archivo

router = APIRouter(prefix="/etl", tags=["ETL"])
SEGURIDAD_ETL = HTTPBearer()
MAX_PREVIEW_REJECTIONS = 100
MAX_PREVIEW_ROWS = 20


def cuenta_actual_etl(
    credenciales: HTTPAuthorizationCredentials = Depends(SEGURIDAD_ETL),
) -> dict:
    from ..main import usuario_actual

    return usuario_actual(credenciales)


def administrador_actual_etl(cuenta: dict = Depends(cuenta_actual_etl)) -> dict:
    from ..main import solo_administrador

    return solo_administrador(cuenta)


def get_etl_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def _leer_y_procesar(archivo: UploadFile, perfil_fuente: str) -> dict:
    try:
        perfil = obtener_perfil(perfil_fuente)
        contenido = archivo.file.read()
        archivo.file.seek(0)
        hash_archivo = hashlib.sha256(contenido).hexdigest()
        tabular = leer_archivo(
            io.BytesIO(contenido),
            archivo.filename or "archivo_sin_nombre",
            archivo.content_type,
            delimiter=perfil.separador,
            encoding=perfil.codificacion,
        )
        validacion = validar_archivo(tabular, perfil.configuracion())
        transformados = transformar_validos(perfil, validacion)
    except (ValueError, ETLFileError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {
        "perfil": perfil,
        "hash_archivo": hash_archivo,
        "archivo": tabular,
        "resultado": validacion,
        "transformados": transformados,
    }


def _vista_previa(proceso: dict) -> VistaPreviaETLResponse:
    perfil = proceso["perfil"]
    archivo = proceso["archivo"]
    resultado = proceso["resultado"]
    return VistaPreviaETLResponse(
        perfil_fuente=perfil.identificador,
        entidad=perfil.entidad,
        nombre_archivo=archivo.nombre,
        tipo_archivo=archivo.tipo,
        total_filas=len(archivo.filas),
        filas_validas=len(resultado.filas_validas),
        filas_rechazadas=len(resultado.filas_rechazadas),
        columnas_no_reconocidas=list(resultado.columnas_no_reconocidas),
        columnas_faltantes=list(resultado.columnas_faltantes),
        muestra_transformada=list(proceso["transformados"][:MAX_PREVIEW_ROWS]),
        muestra_rechazos=[
            RechazoETLResponse(
                numero_fila=rechazo.numero_fila,
                datos_originales=rechazo.datos_originales,
                motivo=rechazo.motivo,
            )
            for rechazo in resultado.filas_rechazadas[:MAX_PREVIEW_REJECTIONS]
        ],
    )


@router.post(
    "/validar",
    response_model=VistaPreviaETLResponse,
    summary="Validar un archivo ETL sin persistirlo",
)
def validar_importacion(
    archivo: Annotated[UploadFile, File(description="Archivo CSV o XLSX")],
    perfil_fuente: Annotated[str, Form(description="Perfil oficial de la fuente")],
    _: dict = Depends(cuenta_actual_etl),
) -> VistaPreviaETLResponse:
    return _vista_previa(_leer_y_procesar(archivo, perfil_fuente))


@router.post(
    "/importar",
    response_model=ImportacionDetalleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Importar un dataset oficial con transacción",
)
def importar_dataset(
    archivo: Annotated[UploadFile, File(description="Archivo CSV o XLSX")],
    perfil_fuente: Annotated[str, Form(description="Perfil oficial de la fuente")],
    cuenta: dict = Depends(administrador_actual_etl),
    session: Session = Depends(get_etl_session),
) -> ImportacionDetalleResponse:
    proceso = _leer_y_procesar(archivo, perfil_fuente)
    try:
        importacion = importar_archivo(
            session,
            archivo={
                "nombre": proceso["archivo"].nombre,
                "tipo": proceso["archivo"].tipo,
                "filas": proceso["archivo"].filas,
                "resultado": proceso["resultado"],
                "transformados": proceso["transformados"],
            },
            perfil_id=perfil_fuente,
            usuario_nombre=cuenta["usuario"],
            hash_archivo=proceso["hash_archivo"],
        )
    except DuplicateImportError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo completar la importación.",
        ) from error
    return ImportacionDetalleResponse.model_validate(importacion)


@router.get(
    "/importaciones",
    response_model=ImportacionesPageResponse,
    summary="Consultar el historial de importaciones",
)
def historial_importaciones(
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
    _: dict = Depends(cuenta_actual_etl),
    session: Session = Depends(get_etl_session),
) -> ImportacionesPageResponse:
    filas, total = listar_importaciones(session, (pagina - 1) * tamano, tamano)
    return ImportacionesPageResponse(
        total=total,
        pagina=pagina,
        tamano=tamano,
        items=[ImportacionResumenResponse.model_validate(fila) for fila in filas],
    )


@router.get(
    "/importaciones/{importacion_id}",
    response_model=ImportacionDetalleResponse,
    summary="Consultar el detalle de una importación",
)
def detalle_importacion(
    importacion_id: int,
    _: dict = Depends(cuenta_actual_etl),
    session: Session = Depends(get_etl_session),
) -> ImportacionDetalleResponse:
    importacion = obtener_importacion(session, importacion_id)
    if importacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importación no encontrada.")
    return ImportacionDetalleResponse.model_validate(importacion)


@router.get(
    "/importaciones/{importacion_id}/rechazados",
    response_model=RechazadosPageResponse,
    summary="Consultar filas rechazadas de una importación",
)
def rechazados_importacion(
    importacion_id: int,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
    _: dict = Depends(cuenta_actual_etl),
    session: Session = Depends(get_etl_session),
) -> RechazadosPageResponse:
    if obtener_importacion(session, importacion_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importación no encontrada.")
    filas, total = listar_rechazados(session, importacion_id, (pagina - 1) * tamano, tamano)
    return RechazadosPageResponse(
        total=total,
        pagina=pagina,
        tamano=tamano,
        items=[
            RechazoETLResponse(
                numero_fila=fila.numero_fila,
                datos_originales=fila.datos_originales,
                motivo=fila.motivo_rechazo,
            )
            for fila in filas
        ],
    )


@router.get(
    "/estadisticas",
    response_model=EstadisticasETLResponse,
    summary="Consultar estadísticas generales del ETL",
)
def estadisticas_etl(
    _: dict = Depends(cuenta_actual_etl),
    session: Session = Depends(get_etl_session),
) -> EstadisticasETLResponse:
    return EstadisticasETLResponse(**obtener_estadisticas(session))
