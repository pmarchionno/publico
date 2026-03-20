# Guía de Puesta en Marcha de Infraestructura

Esta guía describe cómo desplegar la plataforma Pagoflex Modular.

## Requisitos
- Docker Engine 20+
- Docker Compose v2+
- Make (opcional, para comandos rápidos)

## Arquitectura de Despliegue
El sistema se compone de los siguientes contenedores:
1. **API Server (`api`)**: FastAPI recibiendo peticiones HTTP.
2. **Scheduler (`scheduler`)**: Workers de Celery para tareas asíncronas.
3. **Database (`db`)**: PostgreSQL 15 (con esquemas por tenant).
4. **Cache/Broker (`redis`)**: Redis 7 para colas de mensajería y caché.

## Pasos de Inicio Rápido

### 1. Variables de Entorno
Copiar el ejemplo a `.env` productivo:
```bash
cp .env .env.prod
```
Asegurar definir:
- `DATABASE_URL`: Conexión a Postgres.
- `REDIS_URL`: Conexión a Redis.
- `SECRET_KEY`: Llave fuerte para JWT.

### 2. Iniciar Servicios
Para levantar todo el stack:
```bash
docker-compose up -d --build
```

### 3. Migraciones de Base de Datos
Es crítico correr las migraciones para crear las tablas y esquemas:
```bash
# Entrar al contenedor
docker-compose exec api bash

# Ejecutar migraciones (Alembic)
alembic upgrade head
```

### 4. Verificación de Salud
Validar que los servicios estén operativos:
```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "api_server"}
```

## Solución de Problemas
- **Puerto Ocupado**: Si el 8000 está en uso, editar `API_PORT` en `.env`.
- **Conexión DB Rechazada**: Verificar que el contenedor `db` esté `healthy`.
