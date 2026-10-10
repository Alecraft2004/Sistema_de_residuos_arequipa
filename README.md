# Sistema Predictivo de Residuos — Arequipa

Aplicación de gestión y predicción de acumulación de residuos urbanos para Arequipa.

## Preparación local

1. En pgAdmin, crea una base de datos llamada `residuos_arequipa`.
2. Copia `.env.example`, renómbralo como `.env` y reemplaza `TU_CONTRASENA` por la contraseña local del usuario `postgres`.
3. Ejecuta la aplicación:

```powershell
.\.venv\Scripts\streamlit run app.py
```

Al abrirse la aplicación, las tablas y las cinco zonas demostrativas se crearán automáticamente.

## Avance actual: 50%

- Registro y consulta de residuos en PostgreSQL.
- Datos demostrativos de zonas urbanas.
- Random Forest para estimar la cantidad de residuos.
- Random Forest para clasificar el nivel de acumulación: bajo, medio o alto.
- Priorización y recomendación de atención.
- Historial de las últimas predicciones guardado en PostgreSQL.

Los datos de entrenamiento son simulados y sirven para demostrar el funcionamiento del modelo; no representan datos oficiales de la Municipalidad de Arequipa.
