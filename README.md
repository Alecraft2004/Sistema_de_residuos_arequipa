# AQPredict Residuos — Backend

API REST de AQPredict para la gestión, procesamiento y análisis predictivo de residuos sólidos urbanos en Arequipa.

El backend centraliza la lógica de negocio, procesamiento ETL, validación de fuentes oficiales, consultas territoriales, predicción de generación municipal y servicios de análisis.

## 1. Tecnologías

- Python 3.12
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- PostgreSQL / Supabase
- pg8000
- Pandas y herramientas de procesamiento de datos
- Scikit-learn y modelos de Machine Learning, según los servicios implementados

Las versiones exactas de las dependencias se encuentran en `requirements.txt`.

## 2. Estructura general

```text
sistema_residuos_arequipa/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   │   ├── etl.py
│   │   └── ...
│   └── services/
│       ├── etl/
│       │   ├── ingestion_service.py
│       │   ├── validation_service.py
│       │   ├── transformation_service.py
│       │   ├── loading_service.py
│       │   ├── api_service.py
│       │   └── source_profiles.py
│       └── ...
│
├── alembic/
│   └── versions/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── models/
│   └── staging/
│
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

La estructura representa los componentes principales. Los nombres y módulos adicionales deben mantenerse de acuerdo con la estructura real del repositorio.

### Directorios de datos

- `data/raw/`: fuentes originales utilizadas por los procesos existentes.
- `data/processed/`: información procesada.
- `data/models/`: artefactos de modelos predictivos.
- `data/staging/`: archivos temporales para inspección y validación de nuevas fuentes.

**Importante:** `data/staging/` no debe subirse al repositorio. Los archivos originales y artefactos que sí forman parte del proyecto deben conservarse según su política de versionado.

## 3. Requisitos previos

Instalar:

- Python 3.12.
- Git.
- PostgreSQL o acceso a la instancia PostgreSQL de Supabase.
- Git Bash o PowerShell.

## 4. Instalación

### 4.1. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
cd sistema_residuos_arequipa
```

Si se trabaja con una rama específica:

```bash
git checkout YeisonBack
```

### 4.2. Crear el entorno virtual

En Windows:

```powershell
py -3.12 -m venv .venv
```

Activar el entorno:

**PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Git Bash:**

```bash
source .venv/Scripts/activate
```

### 4.3. Actualizar pip e instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Este procedimiento instala las dependencias registradas por el proyecto, incluidas las incorporadas durante su desarrollo.

No es necesario instalar individualmente cada paquete cuando ya está correctamente registrado en `requirements.txt`.

## 5. Configuración de variables de entorno

Crear el archivo local `.env` a partir de la plantilla:

```powershell
Copy-Item .env.example .env
```

En Git Bash:

```bash
cp .env.example .env
```

Completar las variables requeridas utilizando las credenciales propias del entorno de desarrollo.

Entre las configuraciones que puede requerir el proyecto se encuentran:

- Conexión a PostgreSQL.
- Configuración de Supabase, si el servicio correspondiente está habilitado.
- Parámetros de autenticación.
- Configuración de servicios externos, si corresponde.

Ejemplo de formato:

```env
DATABASE_URL=postgresql+pg8000://USUARIO:CONTRASENA@HOST:PUERTO/BASE_DE_DATOS
```

Utilizar exactamente los nombres de variables definidos en `.env.example` y en la configuración de la aplicación.

**Nunca utilizar credenciales reales dentro del README ni subir el archivo `.env` a Git.**

## 6. Base de datos y migraciones

El proyecto utiliza SQLAlchemy y Alembic para administrar la estructura de la base de datos.

Antes de iniciar, verificar que la conexión configurada en `.env` sea válida.

Consultar el estado de las migraciones:

```bash
alembic current
```

Consultar las migraciones disponibles:

```bash
alembic heads
```

Aplicar las migraciones pendientes:

```bash
alembic upgrade head
```

No ejecutar migraciones destructivas ni modificar la base de datos compartida sin autorización.

No utilizar `create_all()` como sustituto del sistema de migraciones.

## 7. Ejecutar el backend

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

También puede ejecutarse mediante:

```bash
python -m uvicorn app.main:app --reload
```

Direcciones locales:

- API: http://127.0.0.1:8000
- Documentación Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

## 8. Servicios y funcionalidades implementadas

### Procesamiento ETL

El backend dispone de servicios para:

- Ingesta de archivos.
- Validación de fuentes.
- Transformación y normalización.
- Carga de registros.
- Control de importaciones.
- Registro de datos rechazados.
- Detección de archivos repetidos mediante hash SHA-256.

Perfiles de fuentes existentes:

- `MINAM_GENERACION_ANUAL`
- `OEFA_AREAS_DEGRADADAS`

### Endpoints ETL disponibles

| Método | Endpoint | Función |
|---|---|---|
| POST | `/etl/validar` | Validar un archivo |
| POST | `/etl/importar` | Importar una fuente |
| GET | `/etl/importaciones` | Consultar importaciones |
| GET | `/etl/importaciones/{id}` | Consultar detalle |
| GET | `/etl/importaciones/{id}/rechazados` | Consultar registros rechazados |
| GET | `/etl/estadisticas` | Consultar estadísticas ETL |

### Predicción de generación municipal

El backend incluye servicios de consulta y predicción basados en la fuente MINAM.

La implementación actual utiliza un enfoque de persistencia como línea base predictiva. Los resultados deben interpretarse considerando el período histórico y las limitaciones del modelo.

### Otras funcionalidades

El proyecto contempla servicios relacionados con análisis territorial, información ambiental, priorización y planificación. Su disponibilidad y estado deben verificarse en la documentación interactiva de la API.

Consultar `/docs` para conocer las rutas realmente registradas en la versión ejecutada.

## 9. Pruebas y verificación

Comprobar que el servidor inicia correctamente y que la documentación de Swagger carga.

Consultar:

```text
http://127.0.0.1:8000/docs
```

Verificar las rutas disponibles y probar los servicios con datos de desarrollo.

Si el proyecto tiene pruebas automatizadas:

```bash
python -m pytest
```

No considerar una prueba exitosa si depende de credenciales, datos o servicios externos que no están disponibles.

## 10. Incorporar nuevas dependencias

Cuando se necesite agregar una biblioteca:

```bash
python -m pip install nombre_del_paquete
```

Después, actualizar `requirements.txt` para registrar las dependencias del entorno.

Para generar un listado completo de versiones instaladas:

```bash
python -m pip freeze > requirements.txt
```

Revisar el archivo generado antes de confirmar los cambios, evitando incorporar paquetes ajenos al proyecto o dependencias innecesarias.

Una vez actualizado, los demás integrantes podrán instalar las dependencias mediante:

```bash
python -m pip install -r requirements.txt
```

## 11. Seguridad y buenas prácticas

- No subir `.env`.
- No publicar contraseñas de PostgreSQL.
- No publicar claves de Supabase.
- No publicar tokens JWT ni claves secretas.
- Mantener `.env.example` sin valores sensibles.
- No subir archivos temporales de `data/staging/`.
- No modificar migraciones ya aplicadas sin evaluar sus consecuencias.
- No eliminar datos o artefactos utilizados por los modelos.
- No incluir datos personales o sensibles en los repositorios.

## 12. Estado del proyecto

AQPredict se encuentra en desarrollo e integración.

Las fuentes adicionales, como valorización de residuos, información territorial y rutas de recolección, deben validarse antes de incorporarse a los procesos definitivos.

La versión final integrará los servicios del backend con los módulos de visualización del frontend.

---

**AQPredict Residuos — Backend**  
Sistema de análisis y apoyo a la gestión de residuos sólidos urbanos en Arequipa.