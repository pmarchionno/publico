# Pagoflex Gateway

## Resumen
- API FastAPI expuesta vía Docker Compose (servicio `api`) corriendo `app.main:app` en el puerto 8000. Al iniciar el contenedor se ejecuta `alembic upgrade head` para crear/actualizar las tablas `payments`, `transfers` y `transfer_events` en PostgreSQL.
- Dependencias administradas en `requirements.txt`; los contenedores ya incluyen FastAPI, Celery, SQLAlchemy y utilidades básicas.

## Documentación útil
- Guía de despliegue en VPS con pasos actualizados y ejemplos de prueba: ver [docs/DESPLIEGUE_VPS.md](docs/DESPLIEGUE_VPS.md).
- Catálogo de endpoints disponibles y notas operativas: ver [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md).

## Flujo de prueba reciente (26/12/2025)
1. `docker compose up -d --build` (ensambló `api` apuntando a `app.main:app`).
2. Creación de pago de prueba:
	```bash
	curl -X POST http://localhost:8000/api/v1/payments \
		  -H "Content-Type: application/json" \
		  -d '{"amount": 100.0, "currency": "USD"}'
	```
	Respuesta: pago `5decdb50-25d3-4850-ba84-c5de1e41c278` en estado `PENDING`.
3. Consulta del registro:
	```bash
	curl http://localhost:8000/api/v1/payments/5decdb50-25d3-4850-ba84-c5de1e41c278
	```
	Se verificó el mismo estado. Usa el repositorio en memoria, por lo que los datos desaparecen al reiniciar el contenedor.
