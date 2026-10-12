"""API REST para AQPredict Residuos.

Ejecutar con: uvicorn main:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from collections import defaultdict, deque
from datetime import date, datetime, time, timedelta, timezone
import os
from threading import Lock

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .database import (
    autenticar,
    guardar_prediccion,
    obtener_predicciones_recientes,
    obtener_registros,
    obtener_usuario,
    obtener_zonas,
    preparar_base_datos,
    registrar_residuo,
)
from .services.ml_service import obtener_metricas_modelo, predecir_residuos
from .services.planificador import construir_ruta, priorizar_zonas

load_dotenv()

app = FastAPI(
    title="AQPredict Residuos API",
    version="1.0.0",
    description="Backend para la gestión predictiva de residuos urbanos de Arequipa.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ESQUEMA_TOKEN = "HS256"
SEGURIDAD = HTTPBearer()
MAX_INTENTOS_LOGIN = 5
VENTANA_INTENTOS = timedelta(minutes=10)
BLOQUEO_INTENTOS = timedelta(minutes=15)
intentos_login: dict[str, deque[datetime]] = defaultdict(deque)
bloqueos_login: dict[str, datetime] = {}
bloqueo_login = Lock()


class Credenciales(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    clave: str = Field(min_length=1, max_length=100)


class RegistroEntrada(BaseModel):
    zona_id: int = Field(gt=0)
    fecha: date
    hora: time
    cantidad_kg: int = Field(gt=0)
    dias_sin_recoleccion: int = Field(ge=0, le=30)


class PrediccionEntrada(BaseModel):
    zona_id: int = Field(gt=0)
    fecha: date
    hora: time
    acumulacion_previa_kg: int = Field(ge=0)
    dias_sin_recoleccion: int = Field(ge=0, le=30)


def clave_token() -> str:
    """Usa una clave local de desarrollo si SECRET_KEY no está configurada."""
    return os.getenv("SECRET_KEY", "aqpredict-clave-local-solo-desarrollo")


def verificar_intentos_login(ip: str) -> None:
    """Limita intentos fallidos para reducir ataques de fuerza bruta."""
    ahora = datetime.now(timezone.utc)
    with bloqueo_login:
        hasta = bloqueos_login.get(ip)
        if hasta and hasta > ahora:
            segundos = max(1, int((hasta - ahora).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Intenta nuevamente más tarde.",
                headers={"Retry-After": str(segundos)},
            )
        bloqueos_login.pop(ip, None)


def registrar_fallo_login(ip: str) -> None:
    ahora = datetime.now(timezone.utc)
    limite = ahora - VENTANA_INTENTOS
    with bloqueo_login:
        intentos = intentos_login[ip]
        while intentos and intentos[0] < limite:
            intentos.popleft()
        intentos.append(ahora)
        if len(intentos) >= MAX_INTENTOS_LOGIN:
            bloqueos_login[ip] = ahora + BLOQUEO_INTENTOS
            intentos.clear()


def limpiar_intentos_login(ip: str) -> None:
    with bloqueo_login:
        intentos_login.pop(ip, None)


def crear_token(cuenta: dict) -> str:
    vencimiento = datetime.now(timezone.utc) + timedelta(hours=8)
    datos = {"sub": cuenta["usuario"], "rol": cuenta["rol"], "exp": vencimiento}
    return jwt.encode(datos, clave_token(), algorithm=ESQUEMA_TOKEN)


def usuario_actual(credenciales: HTTPAuthorizationCredentials = Depends(SEGURIDAD)) -> dict:
    try:
        datos = jwt.decode(credenciales.credentials, clave_token(), algorithms=[ESQUEMA_TOKEN])
        usuario = datos.get("sub")
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o vencido.") from error

    cuenta = obtener_usuario(usuario) if isinstance(usuario, str) else None
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión no válida.")
    return cuenta


def solo_administrador(cuenta: dict = Depends(usuario_actual)) -> dict:
    if cuenta["rol"] != "Administrador":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol Administrador.")
    return cuenta


def buscar_zona(zona_id: int):
    zona = next((item for item in obtener_zonas() if item.id == zona_id), None)
    if not zona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zona no encontrada.")
    return zona


@app.on_event("startup")
def iniciar_base_datos() -> None:
    preparar_base_datos()


@app.get("/health", tags=["Sistema"])
def estado() -> dict:
    return {"estado": "ok", "servicio": "AQPredict Residuos API"}


@app.post("/auth/login", tags=["Autenticación"])
def iniciar_sesion(entrada: Credenciales, request: Request) -> dict:
    ip = request.client.host if request.client else "desconocida"
    verificar_intentos_login(ip)
    cuenta = autenticar(entrada.usuario.strip(), entrada.clave)
    if not cuenta:
        registrar_fallo_login(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
    limpiar_intentos_login(ip)
    return {"access_token": crear_token(cuenta), "token_type": "bearer", "usuario": cuenta}


@app.get("/zonas", tags=["Zonas"])
def listar_zonas(_: dict = Depends(usuario_actual)) -> list[dict]:
    return [
        {
            "id": zona.id,
            "nombre": zona.nombre,
            "poblacion_estimada": zona.poblacion_estimada,
            "distrito": zona.distrito.nombre,
        }
        for zona in obtener_zonas()
    ]


@app.get("/residuos", tags=["Residuos"])
def listar_residuos(distrito: str | None = None, _: dict = Depends(usuario_actual)) -> list[dict]:
    registros = obtener_registros()
    if distrito:
        registros = [item for item in registros if item["Distrito"].casefold() == distrito.casefold()]
    return registros


@app.post("/residuos", status_code=status.HTTP_201_CREATED, tags=["Residuos"])
def crear_registro(entrada: RegistroEntrada, _: dict = Depends(solo_administrador)) -> dict:
    zona = buscar_zona(entrada.zona_id)
    registrar_residuo(
        entrada.zona_id,
        entrada.fecha,
        entrada.hora,
        entrada.cantidad_kg,
        entrada.dias_sin_recoleccion,
    )
    return {"mensaje": "Registro creado correctamente.", "zona": zona.nombre}


@app.get("/predicciones", tags=["Predicciones"])
def listar_predicciones(_: dict = Depends(usuario_actual)) -> list[dict]:
    return obtener_predicciones_recientes()


@app.post("/predicciones", tags=["Predicciones"])
def generar_prediccion(entrada: PrediccionEntrada, _: dict = Depends(usuario_actual)) -> dict:
    zona = buscar_zona(entrada.zona_id)
    resultado = predecir_residuos(
        poblacion_estimada=zona.poblacion_estimada,
        dia_semana=entrada.fecha.weekday(),
        hora=entrada.hora.hour,
        dias_sin_recoleccion=entrada.dias_sin_recoleccion,
        acumulacion_previa_kg=entrada.acumulacion_previa_kg,
    )
    guardar_prediccion(
        zona.id,
        entrada.fecha,
        entrada.hora,
        int(resultado["cantidad_estimada_kg"]),
        str(resultado["nivel"]),
        str(resultado["prioridad"]),
        str(resultado["recomendacion"]),
    )
    return {"zona": zona.nombre, "distrito": zona.distrito.nombre, **resultado}


@app.get("/priorizacion", tags=["Planificación"])
def obtener_priorizacion(capacidad_kg: int = 5000, _: dict = Depends(usuario_actual)) -> dict:
    if not 2000 <= capacidad_kg <= 10000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Capacidad entre 2000 y 10000 kg.")
    momento = datetime.now()
    prioridades = priorizar_zonas(obtener_zonas(), momento.weekday(), momento.hour)
    return {"prioridades": prioridades, "ruta_sugerida": construir_ruta(prioridades, capacidad_kg)}


@app.get("/reportes/resumen", tags=["Reportes"])
def resumen(_: dict = Depends(usuario_actual)) -> dict:
    registros = obtener_registros()
    return {
        "zonas_registradas": len(obtener_zonas()),
        "registros_disponibles": len(registros),
        "residuos_registrados_kg": sum(item["Cantidad (kg)"] for item in registros),
        "metricas_modelo": obtener_metricas_modelo(),
    }
