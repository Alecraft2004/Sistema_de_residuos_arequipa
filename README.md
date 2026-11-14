# AQPredict Residuos — Frontend

Interfaz web de AQPredict Residuos, desarrollada con React y Vite.

El frontend permite visualizar los resultados del sistema, consultar indicadores, interactuar con mapas y acceder a los módulos funcionales mediante la API REST del backend.

## 1. Tecnologías

- React
- Vite
- JavaScript
- pnpm
- ESLint
- Librerías de visualización y mapas utilizadas por el proyecto.

Las versiones exactas y dependencias se encuentran registradas en:

- `package.json`
- `pnpm-lock.yaml`

## 2. Requisitos previos

Instalar:

- Node.js en una versión compatible con el proyecto.
- pnpm.
- Git.

Comprobar las instalaciones:

```bash
node --version
pnpm --version
```

Si pnpm no está disponible y la versión de Node.js lo permite:

```bash
npm install -g pnpm
```

## 3. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
cd Sistema_de_residuos_arequipa
```

Para trabajar con la rama correspondiente:

```bash
git checkout YeisonFront
```

## 4. Instalar dependencias

Desde la raíz del frontend:

```bash
pnpm install
```

Este comando instala las dependencias declaradas en `package.json` y utiliza `pnpm-lock.yaml` para mantener versiones consistentes.

Para instalaciones reproducibles, especialmente en entornos de integración:

```bash
pnpm install --frozen-lockfile
```

No eliminar ni reemplazar `pnpm-lock.yaml` sin una razón justificada.

## 5. Variables de entorno

Si el frontend necesita una URL personalizada del backend, crear un archivo `.env` tomando como referencia `.env.example`.

Ejemplo de configuración:

```env
VITE_API_URL=http://127.0.0.1:8000
```

**Importante:** `VITE_API_URL` es un ejemplo. Utilizar el nombre exacto de la variable que consume el código actual del frontend.

Las variables con prefijo `VITE_` pueden quedar expuestas en el navegador. Por tanto:

- No guardar contraseñas en variables `VITE_`.
- No colocar claves privadas de Supabase.
- No colocar secretos JWT.
- No colocar credenciales de PostgreSQL.
- No incluir API keys privadas en el código del frontend.

Las credenciales y operaciones sensibles deben permanecer en el backend.

## 6. Ejecutar el frontend

Primero, comprobar que el backend esté funcionando.

Backend local:

```text
http://127.0.0.1:8000
```

Después, desde la carpeta del frontend:

```bash
pnpm dev
```

Vite mostrará la dirección local. Habitualmente:

```text
http://localhost:5173
```

Abrir esa dirección en el navegador.

Mantener la terminal abierta mientras se utiliza la aplicación.

## 7. Verificación del proyecto

### Revisar errores de lint

```bash
pnpm lint
```

### Construir la versión de producción

```bash
pnpm build
```

### Vista previa de la compilación

```bash
pnpm preview
```

La vista previa permite comprobar la versión compilada del frontend.

## 8. Conexión con el backend

El frontend consume los servicios de AQPredict mediante solicitudes HTTP a la API REST.

Para comprobar la conexión:

1. Iniciar el backend.
2. Iniciar el frontend.
3. Ingresar a la aplicación.
4. Verificar que los módulos que consumen la API reciban respuestas.
5. Comprobar el comportamiento de los filtros, mapas y gráficos.
6. Revisar la consola del navegador si existen errores de conexión.

Si se utiliza una configuración CORS, el origen del frontend debe estar autorizado en el backend.

## 9. Incorporar nuevas dependencias

Para agregar una biblioteca:

```bash
pnpm add nombre-del-paquete
```

Para agregar una dependencia de desarrollo:

```bash
pnpm add -D nombre-del-paquete
```

Después de instalar una dependencia:

- Verificar que `package.json` se haya actualizado.
- Verificar que `pnpm-lock.yaml` se haya actualizado.
- Probar el proyecto.
- Subir ambos archivos al repositorio.

Los demás integrantes podrán instalar las nuevas dependencias con:

```bash
pnpm install
```

No es necesario compartir manualmente la carpeta `node_modules/`.

## 10. Seguridad y buenas prácticas

- No subir archivos `.env`.
- Mantener `.env.example` sin credenciales reales.
- No incluir claves privadas en el frontend.
- No subir `node_modules/`.
- No subir la carpeta `dist/`.
- No compartir tokens de acceso.
- Mantener actualizado `pnpm-lock.yaml`.
- No almacenar datos sensibles directamente en los componentes.
- Obtener los resultados del sistema mediante los servicios del backend cuando corresponda.

## 11. Estado del proyecto

AQPredict se encuentra en proceso de consolidación e integración.

La versión final del frontend estará organizada alrededor de los cuatro módulos principales:

1. Predicción de generación municipal.
2. Priorización territorial.
3. Análisis ambiental OEFA.
4. Identificación de zonas críticas.

La sección técnica de demostración KDD / ML MINAM no formará parte de la navegación de la versión final.

Las pantallas existentes serán revisadas para conservar los componentes útiles y reemplazar progresivamente los datos demostrativos por información procedente del backend.

---

**AQPredict Residuos — Frontend**  
Interfaz de visualización y consulta del sistema predictivo de gestión de residuos sólidos urbanos en Arequipa.