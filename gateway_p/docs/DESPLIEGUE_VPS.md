# Guía de despliegue en VPS Linux

## 1. Preparación del servidor
- Actualizar paquetes base:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
- Instalar dependencias necesarias para Docker:
  ```bash
  sudo apt install -y ca-certificates curl gnupg lsb-release
  ```

## 2. Instalar Docker Engine
- Añadir la clave GPG oficial de Docker y el repositorio estable:
  ```bash
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt update
  ```
- Instalar Docker Engine y plugins de Compose:
  ```bash
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  ```
- Habilitar y arrancar el servicio Docker:
  ```bash
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER
  # Cerrar sesión y volver a ingresar para aplicar el grupo docker
  ```

## 3. Clonar el proyecto
- Seleccionar directorio de trabajo y clonar el repositorio:
  ```bash
  git clone <URL_DEL_REPO> billetera2026
  cd billetera2026/pagoflex/gateway_p
  ```
- Opcional: copiar archivo `.env` si existe en origen o configurarlo según necesidades.

## 4. Verificar servicios locales en conflicto
- Asegurarse de que no haya Redis ni Postgres locales ocupando los puertos 6379 y 5432:
  ```bash
  sudo systemctl stop redis-server postgresql || true
  sudo systemctl disable redis-server postgresql || true
  ss -ltnp | grep -E "(6379|5432)" || true
  ```

## 5. Construir y levantar la infraestructura Docker
- Construir imágenes y lanzar servicios:
  ```bash
  docker compose up -d --build
  ```
- Confirmar que los contenedores estén sanos:
  ```bash
  docker compose ps
  ```
- El servicio `api` expone la aplicación `app.main:app` (FastAPI) en el puerto 8000, habilitando los endpoints `/api/v1/payments`.

## 6. Acceso a la aplicación
- API disponible en `http://<IP_VPS>:8000`.
- Postgres expuesto en el puerto 5432 (credenciales en `docker-compose.yml`).
- Redis expuesto en el puerto 6379.
- Variables de entorno relevantes para el conector Banco Comercio (definir en `.env` o exportar antes de `docker compose up`):
  ```bash
  export BDC_BASE_URL=https://api-homo.bdcconecta.com
  export BDC_CLIENT_ID=<tu_client_id>
  export BDC_CLIENT_SECRET=<tu_client_secret>
  export BDC_SECRET_KEY=<tu_secret_key>
  export TRANSFER_CONNECTOR_MODE=mock  # usar "banco_comercio" para hablar con el banco real
  export PERSISTENCE_BACKEND=database   # "memory" sólo para pruebas sin Postgres
  ```
- El contenedor `api` ejecuta `alembic -c alembic.ini upgrade head` antes de levantar FastAPI; en despliegues manuales ejecutar la migración para crear `payments`, `transfers` y `transfer_events`.

## 7. Ejecutar pruebas dentro del contenedor API
- Instalar utilidades necesarias (solo la primera vez):
  ```bash
  docker compose exec api pip install pytest httpx
  ```
- Ejecutar suite de pruebas con el entorno de la aplicación:
  ```bash
  docker compose exec -e PYTHONPATH=/app api pytest tests/test_api.py
  ```
- Probar el flujo de transferencias (usa el stub del conector en pruebas, pero el endpoint real espera credenciales válidas):
  ```bash
  curl -X POST http://localhost:8000/api/v1/transfers \
    -H "Content-Type: application/json" \
    -d @payload_transfer.json

  curl http://localhost:8000/api/v1/transfers/<ORIGIN_ID_GENERADO>
  ```
- En modo `TRANSFER_CONNECTOR_MODE=mock` se obtiene respuesta exitosa por defecto; enviar `"concept": "REJECT"` o `"concept": "FAIL"` en el body fuerza un rechazo simulado.
- Para inspeccionar lo persistido: `docker compose exec -T db psql -U postgres -d pagoflex -c "SELECT origin_id,status,created_at FROM transfers ORDER BY created_at DESC LIMIT 10;"`

## 8. Consultar datos desde la API
- Crear un pago de prueba y obtener el `id` generado:
  ```bash
  curl -X POST http://localhost:8000/api/v1/payments \
    -H "Content-Type: application/json" \
    -d '{"amount": 100.0, "currency": "USD"}'
  ```
- Respuesta esperada (ejemplo real de la prueba del 26/12/2025):
  ```json
  {
    "id": "5decdb50-25d3-4850-ba84-c5de1e41c278",
    "amount": 100.0,
    "currency": "USD",
    "status": "PENDING",
    "created_at": "2025-12-26T19:15:16.270386",
    "updated_at": "2025-12-26T19:15:16.270391"
  }
  ```
- Procesar el pago para actualizar su estado (opcional, según prueba):
  ```bash
  curl -X POST http://localhost:8000/api/v1/payments/<PAYMENT_ID>/process
  ```
- Consultar el estado almacenado en memoria de un pago puntual:
  ```bash
  curl http://localhost:8000/api/v1/payments/<PAYMENT_ID>
  ```
- Ejemplo con el `id` previo:
  ```bash
  curl http://localhost:8000/api/v1/payments/5decdb50-25d3-4850-ba84-c5de1e41c278
  ```
  Resultado observado durante la prueba:
  ```json
  {
    "id": "5decdb50-25d3-4850-ba84-c5de1e41c278",
    "amount": 100.0,
    "currency": "USD",
    "status": "PENDING",
    "created_at": "2025-12-26T19:15:16.270386",
    "updated_at": "2025-12-26T19:15:16.270391"
  }
  ```
- Nota: el servicio actual usa un repositorio en memoria; los datos existen mientras el contenedor `api` está activo y no hay endpoint de listado general.

## 9. Mantenimiento básico
- Ver logs en vivo:
  ```bash
  docker compose logs -f api scheduler
  ```
- Reiniciar servicios:
  ```bash
  docker compose restart
  ```
- Detener y limpiar contenedores:
  ```bash
  docker compose down
  ```

> Nota: Si se actualiza `requirements.txt`, reconstruir la imagen con `docker compose build api scheduler` antes de volver a levantar los servicios.
