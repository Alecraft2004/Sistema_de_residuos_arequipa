"""Acceso a PostgreSQL y preparación de los datos demostrativos."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import date, time

from dotenv import load_dotenv
from sqlalchemy import Date, ForeignKey, Integer, String, Time, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, joinedload, mapped_column, relationship

load_dotenv()


class Base(DeclarativeBase):
    pass


class Distrito(Base):
    __tablename__ = "distritos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    zonas: Mapped[list["Zona"]] = relationship(back_populates="distrito")


class Zona(Base):
    __tablename__ = "zonas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    poblacion_estimada: Mapped[int] = mapped_column(Integer, nullable=False)
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"), nullable=False)
    distrito: Mapped[Distrito] = relationship(back_populates="zonas")
    registros: Mapped[list["RegistroResiduo"]] = relationship(back_populates="zona")


class RegistroResiduo(Base):
    __tablename__ = "registros_residuos"

    id: Mapped[int] = mapped_column(primary_key=True)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zonas.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    cantidad_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_sin_recoleccion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fuente: Mapped[str] = mapped_column(String(30), nullable=False, default="Demostrativo")
    zona: Mapped[Zona] = relationship(back_populates="registros")


class Prediccion(Base):
    __tablename__ = "predicciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zonas.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    cantidad_estimada_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    nivel_acumulacion: Mapped[str] = mapped_column(String(20), nullable=False)
    prioridad: Mapped[str] = mapped_column(String(20), nullable=False)
    recomendacion: Mapped[str] = mapped_column(String(250), nullable=False)
    modelo: Mapped[str] = mapped_column(String(80), nullable=False, default="Random Forest demostrativo")
    zona: Mapped[Zona] = relationship()


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    clave_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("No se configuró DATABASE_URL. Revisa el archivo .env.")
    return create_engine(database_url, pool_pre_ping=True)


def preparar_base_datos() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if not session.scalar(select(Distrito.id).limit(1)):
            cerro_colorado = Distrito(nombre="Cerro Colorado")
            paucarpata = Distrito(nombre="Paucarpata")
            cercado = Distrito(nombre="Cercado")
            session.add_all([cerro_colorado, paucarpata, cercado])
            session.flush()
            session.add_all(
                [
                    Zona(nombre="Zamácola", poblacion_estimada=28500, distrito=cerro_colorado),
                    Zona(nombre="La Libertad", poblacion_estimada=22100, distrito=cerro_colorado),
                    Zona(nombre="Miguel Grau", poblacion_estimada=31800, distrito=paucarpata),
                    Zona(nombre="Mariscal Cáceres", poblacion_estimada=19400, distrito=paucarpata),
                    Zona(nombre="Centro Histórico", poblacion_estimada=12600, distrito=cercado),
                ]
            )
            session.commit()

    with Session(engine) as session:
        if not session.scalar(select(Usuario.id).limit(1)):
            session.add_all(
                [
                    Usuario(usuario="admin", clave_hash=_hash_clave("admin123"), rol="Administrador"),
                    Usuario(usuario="operador", clave_hash=_hash_clave("operador123"), rol="Operador"),
                ]
            )
            session.commit()


def _hash_clave(clave: str, sal: str | None = None) -> str:
    sal = sal or secrets.token_hex(16)
    clave_hash = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), 120_000).hex()
    return f"{sal}${clave_hash}"


def autenticar(usuario: str, clave: str) -> dict | None:
    with Session(get_engine()) as session:
        cuenta = session.scalar(select(Usuario).where(Usuario.usuario == usuario))
        if not cuenta:
            return None
        sal, hash_guardado = cuenta.clave_hash.split("$", maxsplit=1)
        if _hash_clave(clave, sal).split("$", maxsplit=1)[1] != hash_guardado:
            return None
        return {"usuario": cuenta.usuario, "rol": cuenta.rol}


def obtener_usuario(usuario: str) -> dict | None:
    """Obtiene una cuenta existente para restaurar una sesión previamente validada."""
    with Session(get_engine()) as session:
        cuenta = session.scalar(select(Usuario).where(Usuario.usuario == usuario))
        if not cuenta:
            return None
        return {"usuario": cuenta.usuario, "rol": cuenta.rol}


def obtener_zonas() -> list[Zona]:
    with Session(get_engine()) as session:
        consulta = (
            select(Zona)
            .options(joinedload(Zona.distrito))
            .join(Zona.distrito)
            .order_by(Distrito.nombre, Zona.nombre)
        )
        return list(session.scalars(consulta))


def registrar_residuo(
    zona_id: int,
    fecha_registro: date,
    hora_registro: time,
    cantidad_kg: int,
    dias_sin_recoleccion: int,
) -> None:
    with Session(get_engine()) as session:
        session.add(
            RegistroResiduo(
                zona_id=zona_id,
                fecha=fecha_registro,
                hora=hora_registro,
                cantidad_kg=cantidad_kg,
                dias_sin_recoleccion=dias_sin_recoleccion,
                fuente="Registro manual",
            )
        )
        session.commit()


def obtener_registros() -> list[dict]:
    with Session(get_engine()) as session:
        consulta = (
            select(RegistroResiduo, Zona, Distrito)
            .join(Zona, RegistroResiduo.zona_id == Zona.id)
            .join(Distrito, Zona.distrito_id == Distrito.id)
            .order_by(RegistroResiduo.fecha.desc(), RegistroResiduo.hora.desc())
        )
        return [
            {
                "Fecha": registro.fecha,
                "Hora": registro.hora.strftime("%H:%M"),
                "Distrito": distrito.nombre,
                "Zona": zona.nombre,
                "Cantidad (kg)": registro.cantidad_kg,
                "Días sin recolección": registro.dias_sin_recoleccion,
                "Fuente": registro.fuente,
            }
            for registro, zona, distrito in session.execute(consulta)
        ]


def guardar_prediccion(
    zona_id: int,
    fecha_prediccion: date,
    hora_prediccion: time,
    cantidad_estimada_kg: int,
    nivel_acumulacion: str,
    prioridad: str,
    recomendacion: str,
) -> None:
    with Session(get_engine()) as session:
        session.add(
            Prediccion(
                zona_id=zona_id,
                fecha=fecha_prediccion,
                hora=hora_prediccion,
                cantidad_estimada_kg=cantidad_estimada_kg,
                nivel_acumulacion=nivel_acumulacion,
                prioridad=prioridad,
                recomendacion=recomendacion,
            )
        )
        session.commit()


def obtener_predicciones_recientes() -> list[dict]:
    with Session(get_engine()) as session:
        consulta = (
            select(Prediccion, Zona, Distrito)
            .join(Zona, Prediccion.zona_id == Zona.id)
            .join(Distrito, Zona.distrito_id == Distrito.id)
            .order_by(Prediccion.id.desc())
            .limit(10)
        )
        return [
            {
                "Fecha": prediccion.fecha,
                "Hora": prediccion.hora.strftime("%H:%M"),
                "Distrito": distrito.nombre,
                "Zona": zona.nombre,
                "Estimación (kg)": prediccion.cantidad_estimada_kg,
                "Nivel": prediccion.nivel_acumulacion,
                "Prioridad": prediccion.prioridad,
            }
            for prediccion, zona, distrito in session.execute(consulta)
        ]
