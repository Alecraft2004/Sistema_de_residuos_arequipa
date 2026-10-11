# AQPredict Residuos — Backend

API REST para la gestión predictiva de residuos urbanos de Arequipa. El proyecto usa PostgreSQL, SQLAlchemy, FastAPI y modelos Random Forest demostrativos.

## Estructura del proyecto

```text
sistema_residuos_arequipa/
├── app/
│   ├── main.py              # API FastAPI, endpoints y autenticación
│   ├── database.py          # Modelos SQLAlchemy y acceso a PostgreSQL
│   └── services/
│       ├── ml_service.py    # Predicción con Random Forest
│       └── planificador.py  # Priorización y ruta sugerida
├── main.py                  # Punto de entrada para Uvicorn
├── .env                     # Configuración local (no se sube a Git)
├── .env.example             # Plantilla de configuración
├── requirements.txt
└── README.md
```

## Preparación

1. Crea una base de datos PostgreSQL llamada `residuos_arequipa`.
2. Copia `.env.example` como `.env` y completa `DATABASE_URL` con tu contraseña local.
3. Instala las dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Inicia el backend:

```powershell
.\.venv\Scripts\uvicorn.exe main:app --reload
```

La API estará disponible en `http://127.0.0.1:8000` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

## Endpoints principales

- `POST /auth/login`: genera un token de acceso.
- `GET /zonas`: lista zonas y distritos.
- `GET` y `POST /residuos`: consulta o registra residuos.
- `GET` y `POST /predicciones`: consulta o genera predicciones.
- `GET /priorizacion`: devuelve prioridades y ruta sugerida.
- `GET /reportes/resumen`: devuelve indicadores generales.
- `GET /health`: confirma que el servicio está disponible.

En `/docs`, usa `POST /auth/login`, copia `access_token` y presiona **Authorize**. Escribe `Bearer` seguido del token para probar los endpoints protegidos.

## Cuentas demostrativas

- Administrador: `admin` / `admin123`
- Operador: `operador` / `operador123`

Los datos y modelos son demostrativos; no representan información oficial de la Municipalidad Provincial de Arequipa.
