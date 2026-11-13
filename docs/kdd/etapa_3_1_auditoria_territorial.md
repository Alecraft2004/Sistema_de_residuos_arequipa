# AQPredict — Etapa 3.1: auditoría territorial y preparación del dashboard

## Alcance y método

La auditoría se realizó sobre el código del backend, los modelos SQLAlchemy, los servicios y endpoints existentes, los artefactos KDD y consultas agregadas de solo lectura contra Supabase.

No se ejecutaron migraciones, escrituras, actualizaciones ni eliminaciones. Tampoco se modificaron el ETL, los modelos ML, los CSV ni el frontend.

> **Criterio territorial:** `UBIGEO` es el identificador territorial confiable para MINAM. No se recomienda utilizar nombres de distrito o provincia como identificadores únicos.

## 1. Inventario MINAM

### Tabla y modelo

La fuente se almacena en `generacion_residuos_distrito_anual`, representada por `GeneracionResiduoDistritoAnual`.

Campos disponibles:

- Identificación: `id`, `importacion_id`, `perfil_fuente`, `ubigeo`.
- Jerarquía nominal: `departamento`, `provincia`, `distrito`.
- Tiempo: `anio`.
- Población: `poblacion_total_inei`, `poblacion_urbana_inei`, `poblacion_rural_inei`.
- Generación:
  - `generacion_municipal_t_anio`.
  - `generacion_municipal_t_dia`.
  - `generacion_domiciliaria_urbana_t_anio`.
  - `generacion_domiciliaria_urbana_t_dia`.
- Indicadores per cápita:
  - `generacion_per_capita_municipal`.
  - `generacion_per_capita_domiciliaria`.
- Trazabilidad: `datos_originales`, `fecha_creacion`.

### Cobertura confirmada

| Indicador | Resultado |
|---|---:|
| Registros | 11 310 |
| UBIGEO distintos | 1 891 |
| Departamentos distintos | 25 |
| Provincias distintas | 198 |
| Nombres de distrito distintos | 1 750 |
| Años | 2019–2024 |
| Registros de Arequipa | 654 |
| UBIGEO de Arequipa | 109 |
| Provincias de Arequipa | 8 |
| Nulos en variables numéricas revisadas | 0 |

La diferencia entre nombres de distrito y UBIGEO confirma que el nombre no es una clave territorial suficiente.

### Jerarquía territorial

La jerarquía disponible para MINAM es:

```text
departamento -> provincia -> distrito -> UBIGEO -> año
```

La relación territorial debe agrupar o filtrar por `UBIGEO`. Los nombres pueden mostrarse en el dashboard, pero no deben utilizarse como única condición de unión.

### Arequipa

Arequipa cuenta con:

- 109 UBIGEO.
- 8 provincias.
- 654 observaciones entre 2019 y 2024.
- 109 UBIGEO por año.
- Generación municipal anual observada entre 11,12 y 67 256,53 toneladas/año.
- Generación per cápita municipal observada entre 0,26 y 1,24.

## 2. Inventario OEFA

La fuente se almacena en `areas_degradadas_oefa`, representada por `AreaDegradadaOEFA`.

### Campos físicos disponibles

- `id`, `importacion_id`, `perfil_fuente`.
- `ubigeo`, `id_uf`.
- `municipalidad_administradora`.
- `denominacion`, `zona`, `categoria`.
- `este`, `norte`, `perimetro`, `area_m2`, `area_ha`.
- `municipalidad_disponen`.
- `cantidad_municipalidades_disponen`.
- Indicadores booleanos ambientales.
- `anio_incorporacion`, `fecha_corte`.
- `datos_originales`, `fecha_creacion`.

### Cobertura confirmada

| Indicador | Resultado |
|---|---:|
| Registros | 2 118 |
| `ID_UF` distintos | 2 114 |
| `UBIGEO` vacíos | 2 118 |
| Coordenadas `este` vacías | 2 118 |
| Coordenadas `norte` vacías | 2 118 |
| `area_m2` vacía | 2 118 |
| `perimetro` vacío | 2 118 |
| Fecha de corte | 2026-08-27 |
| Categoría Recuperación | 2 066 |
| Categoría Reconversión | 52 |

Departamento, provincia, distrito y municipalidad administradora están presentes en `datos_originales` para los 2 118 registros. No están disponibles como columnas físicas completas para consultas territoriales eficientes.

### Representación geográfica posible

Actualmente:

- **No es posible representar puntos OEFA correctamente**, porque no existen coordenadas.
- **No es posible unir OEFA con MINAM por UBIGEO**, porque todos los UBIGEO están vacíos.
- Los nombres territoriales de `datos_originales` permiten una clasificación nominal, pero no una unión geográfica confiable.
- No debe inferirse UBIGEO desde el nombre del distrito.
- `ID_UF` no debe tratarse como clave territorial; existen identificadores repetidos asociados a municipalidades distintas.

OEFA puede mostrarse inicialmente como tabla, tarjetas y gráficos por categorías o nombres territoriales, con una advertencia de que no representa límites geográficos ni puntos cartográficos.

## 3. Auditoría cartográfica

No se encontraron en el repositorio:

- Archivos GeoJSON.
- Shapefiles (`.shp`, `.shx`, `.dbf`, `.prj`).
- Límites departamentales, provinciales o distritales.
- Componentes React de mapas.
- `package.json` o una aplicación frontend dentro del repositorio auditado.
- Bibliotecas cartográficas declaradas en este backend.

Las coordenadas geográficas de OEFA tampoco están disponibles en los registros importados.

### Fuentes que faltan

Para representar correctamente Arequipa y Perú se requiere incorporar, previa aprobación:

1. Límites distritales oficiales con UBIGEO.
2. Límites provinciales oficiales con código territorial.
3. Límites departamentales oficiales.
4. Una fuente de referencia geográfica y su licencia.
5. Una estrategia de simplificación para visualización web.
6. Una correspondencia validada entre los nombres OEFA y los códigos territoriales.

No se debe descargar ni generar cartografía ficticia como parte de esta etapa.

## 4. Indicadores calculables

| Indicador | Fuente y campos | Fórmula | Nivel | Limitaciones |
|---|---|---|---|---|
| Generación municipal anual | MINAM: `generacion_municipal_t_anio`, `ubigeo`, `anio` | Valor almacenado | Distrito/UBIGEO, provincia y departamento por suma | Verificar cobertura antes de comparar agregados |
| Generación per cápita municipal | MINAM: `generacion_per_capita_municipal` | Valor almacenado | Distrito/UBIGEO y agregados descriptivos | No sustituye una tasa recalculada sin conocer la definición oficial |
| Población total | MINAM: `poblacion_total_inei` | Valor almacenado | Distrito/UBIGEO y agregaciones | Puede no ser comparable si cambia la cobertura anual |
| Población urbana/rural | MINAM: `poblacion_urbana_inei`, `poblacion_rural_inei` | Valores almacenados | Distrito/UBIGEO | Requiere conservar el año |
| Variación interanual | MINAM: generación por `ubigeo` y años consecutivos | `G_t - G_(t-1)` | Distrito/UBIGEO | No calcular si falta el año anterior |
| Variación porcentual | MINAM: generación por `ubigeo` y años consecutivos | `(G_t-G_(t-1))/abs(G_(t-1))*100` | Distrito/UBIGEO | No definida cuando el valor anterior es cero |
| Ranking territorial | MINAM: generación, `ubigeo`, nombres territoriales | Orden descendente del indicador | Distrito, provincia o departamento | No confundir ranking con causalidad |
| Comparación provincial | MINAM: `provincia`, `ubigeo`, año, generación | Suma por provincia y año | Provincia | Debe evitarse mezclar años o coberturas distintas |
| Comparación distrital | MINAM: `ubigeo`, distrito, año, generación | Filtro o agrupación por UBIGEO | Distrito | El nombre no reemplaza a UBIGEO |
| Predicción siguiente año | API MINAM y último valor real por UBIGEO | `predicción_(t+1)=G_t` | Distrito/UBIGEO | Es persistencia; no aprende tendencia |
| Áreas OEFA por categoría | OEFA: `categoria` | Conteo de registros | Nacional y clasificación nominal | No es una superficie ni un mapa |
| Áreas OEFA por territorio nominal | OEFA `datos_originales`: departamento/provincia/distrito | Conteo por texto normalizado | Territorial nominal | No unir con MINAM sin homologación |
| Fecha de información OEFA | OEFA: `fecha_corte` | Conteo o filtro por fecha | Dataset completo | Es un corte de información, no necesariamente fecha del evento |

No deben calcularse actualmente:

- Superficie total OEFA: `area_m2` y `area_ha` están vacíos.
- Perímetro total OEFA: `perimetro` está vacío.
- Densidad espacial OEFA: faltan geometrías y superficies.
- Uniones OEFA-MINAM por nombres no homologados.

## 5. Servicios y endpoints reutilizables

### Reutilizables directamente

- `GET /kdd/minam/modelo/estado`: estado, último año y siguiente año.
- `GET /kdd/minam/modelo/metricas`: métricas nacionales y Arequipa.
- `GET /kdd/minam/predicciones`: predicciones nacionales con filtros territoriales.
- `GET /kdd/minam/predicciones/{ubigeo}`: predicción por distrito identificado.
- `GET /kdd/minam/predicciones/arequipa`: cobertura prioritaria de Arequipa.
- `GET /kdd/minam/evaluacion/2024`: evaluación histórica, separada de pronósticos.
- `GET /etl/importaciones`: procedencia e historial de cargas.
- `GET /etl/estadisticas`: estadísticas de importación.

### Servicios reutilizables internamente

- Selección y preprocesamiento MINAM en `app/services/kdd/`.
- Servicio de predicción MINAM con carga cacheada de artefactos.
- Servicio de evaluación para consultar resultados por departamento y distrito.
- Perfiles de fuente ETL para identificar campos oficiales.

No existe actualmente un endpoint específico para:

- Catálogo jerárquico de departamentos, provincias, distritos y UBIGEO.
- Series históricas agregadas para el dashboard.
- Indicadores territoriales MINAM agregados bajo demanda.
- Conteos OEFA desde `datos_originales`.
- Catálogo o descarga de cartografía.

Estos faltantes deben resolverse con ampliaciones pequeñas y de solo lectura, no duplicando los servicios existentes.

## 6. Recomendación para el dashboard

### Primera versión

Priorizar un dashboard MINAM sin mapa:

1. Selector de departamento, provincia, distrito y UBIGEO.
2. Serie anual 2019–2024.
3. Tarjetas de población y generación municipal.
4. Variación interanual cuando exista el año previo.
5. Ranking de distritos.
6. Vista específica de Arequipa.
7. Predicción del siguiente año claramente etiquetada como baseline de persistencia.
8. Panel separado de evaluación histórica 2024.

### Segunda versión

Después de incorporar cartografía oficial:

1. Mapa por UBIGEO para MINAM.
2. Coropletas por generación o población.
3. Capas provinciales y departamentales.
4. Homologación documentada de OEFA.
5. Capa OEFA solo cuando existan coordenadas o una geometría territorial verificable.

## 7. Limitaciones y riesgos

1. OEFA no tiene UBIGEO ni coordenadas.
2. OEFA no puede representarse como puntos o polígonos con los datos actuales.
3. Los campos territoriales OEFA están dentro de JSONB y requieren extracción controlada.
4. Los nombres territoriales no son identificadores únicos.
5. El baseline de predicción repite el último valor y no modela tendencias.
6. Los agregados nacionales o departamentales deben respetar año y cobertura.
7. No se debe interpretar una concentración territorial como causalidad.
8. Las tablas originales no deben modificarse para resolver necesidades de presentación.

## 8. Tareas pendientes ordenadas por prioridad

### Prioridad 1 — Dashboard MINAM confiable

- Definir contratos de respuesta para catálogo territorial y series.
- Exponer agregaciones MINAM de solo lectura.
- Validar que toda agrupación conserve `UBIGEO` y `anio`.
- Integrar las rutas KDD existentes sin duplicar la lógica de predicción.

### Prioridad 2 — Cartografía

- Seleccionar una fuente oficial de límites con UBIGEO.
- Confirmar licencia, versión y sistema de coordenadas.
- Incorporar la cartografía al frontend cuando exista aprobación.

### Prioridad 3 — Homologación OEFA

- Normalizar nombres como etapa intermedia.
- Construir una tabla o archivo de correspondencia revisado.
- Validar manualmente las excepciones.
- No habilitar uniones automáticas hasta tener correspondencias verificadas.

### Prioridad 4 — Indicadores ambientales

- Exponer conteos OEFA por categoría y territorio nominal.
- Incorporar una etiqueta visible de “sin georreferenciación”.
- No calcular superficie ni densidad hasta que existan datos válidos.

## Conclusión

MINAM está listo para alimentar un dashboard territorial basado en series anuales por `UBIGEO`, con prioridad para Arequipa y cobertura complementaria nacional.

OEFA está listo para análisis descriptivo nominal y categórico, pero no para un mapa geográfico ni para un join territorial automático con MINAM.

La siguiente implementación debe comenzar por servicios de consulta MINAM de solo lectura y por la selección aprobada de cartografía oficial. No se recomienda modificar el ETL, las tablas originales ni el modelo ML para resolver necesidades del dashboard.
