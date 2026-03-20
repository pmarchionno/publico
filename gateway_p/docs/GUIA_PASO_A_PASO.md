# Guía Detallada de Despliegue - Pagoflex Middleware

Esta guía describe los pasos necesarios para configurar, desplegar y ejecutar la infraestructura de Pagoflex Middleware desde cero.

## 1. Prerrequisitos

Asegúrate de tener instalado en tu sistema:
- **Docker Engine** (v20.10+)
- **Docker Compose** (v2.0+)
- **Git**

## 2. Configuración del Entorno

El proyecto requiere variables de entorno para funcionar. Hemos incluido un archivo de ejemplo.

1.  Crea el archivo `.env` a partir de la copia, si no existe:
    ```bash
    # Si tienes un archivo de ejemplo .env.example o similar
    # En este caso, crearemos uno con los valores por defecto para Docker
    
    cat <<EOF > .env
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/pagoflex
    REDIS_URL=redis://redis:6379/0
    SECRET_KEY=supersecretkeychangethis
    API_PORT=8000
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=pagoflex
    EOF
    ```

    > **Nota:** La `DATABASE_URL` debe coincidir con las credenciales definidas en `POSTGRES_*` y el nombre del servicio `db` en `docker-compose.yml`.

## 3. Preparación de Base de Datos y Migraciones

El sistema utiliza **Alembic** para gestionar las migraciones de base de datos. Se han generado los archivos de configuración (`alembic.ini` y carpeta `migrations`) automáticamente.

No necesitas crear nada manualmente, los scripts ya están listos en el repositorio.

## 4. Despliegue de Servicios (Docker Compose)

Para levantar la infraestructura completa (API, Base de Datos, Redis, Scheduler):

1.  Construye y levanta los contenedores:
    ```bash
    docker-compose up -d --build
    ```

2.  Verifica que los contenedores estén corriendo:
    ```bash
    docker-compose ps
    ```
    Deberías ver `api`, `scheduler`, `db`, y `redis` en estado `Up` o `running`.

## 5. Aplicación de Migraciones

Una vez que los contenedores están arriba (especialmente la base de datos `db`), debes aplicar las migraciones para crear las tablas.

1.  Genera la primera migración (si es la primera vez):
    ```bash
    docker-compose exec api alembic revision --autogenerate -m "Initial tables"
    ```
    *Si este comando falla indicando que no hay cambios, significa que ya existen migraciones o los modelos no fueron detectados. Si es un despliegue limpio, debería generar un archivo en `migrations/versions`.*

2.  Aplica los cambios a la base de datos:
    ```bash
    docker-compose exec api alembic upgrade head
    ```

## 6. Verificación del Sistema

1.  **Health Check**:
    Abre tu navegador o usa curl:
    ```bash
    curl http://localhost:8000/health
    ```
    Respuesta esperada (configuración al 26/12/2025, corriendo `app.main:app`): `{"status": "ok"}`

2.  **Docs API (Swagger UI)**:
    Visita: [http://localhost:8000/docs](http://localhost:8000/docs)
    Deberías ver la documentación interactiva de la API.

3.  **Prueba funcional de pagos**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/payments \
         -H "Content-Type: application/json" \
         -d '{"amount": 100.0, "currency": "USD"}'
    curl http://localhost:8000/api/v1/payments/<ID_DEVUELTO>
    ```
    Ejemplo real: el 26/12/2025 se creó el pago `5decdb50-25d3-4850-ba84-c5de1e41c278` y se verificó en estado `PENDING` con la segunda llamada.

4.  **Logs**:
    Si algo falla, revisa los logs:
    ```bash
    docker-compose logs -f api
    ```

## Solución de Problemas Comunes

- **Error de conexión a DB durante migración**:
  Asegúrate de que el contenedor `db` esté `healthy` o completamente iniciado antes de correr `alembic upgrade`. Puedes esperar unos segundos tras el `docker-compose up`.

- **Puerto 8000 ocupado**:
  Cambia el puerto en `docker-compose.yml` (sección ports) o en el archivo `.env` si se usa la variable `API_PORT`.

- **Conflictos de Alembic**:
  Si `alembic revision --autogenerate` no detecta modelos, verifica `app/domain/models.py` y asegúrate de que estén importados en `migrations/env.py`. (Ya configurado por defecto).
