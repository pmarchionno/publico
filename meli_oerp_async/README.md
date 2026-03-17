# MercadoLibre Async ETL

Módulo de sincronización de órdenes de MercadoLibre con arquitectura ETL asíncrona.

## 📊 Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│ FASE 1: EXTRACCIÓN (Cron cada 15 min)                   │
│ • GET /orders/search con paginación                     │
│ • Guardar JSONs en tabla staging (meli.order.raw)       │
│ • Sin procesamiento, solo descarga                      │
│ • Rápido: solo I/O de red                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ FASE 2: PROCESAMIENTO (Async con queue_job)             │
│ • Leer de meli.order.raw                                │
│ • Crear/actualizar sale.order, stock.picking, etc.      │
│ • Marcar como procesado                                 │
│ • Reintentos automáticos si falla                       │
└─────────────────────────────────────────────────────────┘
```

## ✅ Ventajas

| Aspecto              | Sync por lotes        | Este módulo (Async ETL)      |
| -------------------- | --------------------- | ---------------------------- |
| Riesgo timeout       | Medio                 | **Bajo**                     |
| Trazabilidad         | Media                 | **Alta**                     |
| Recuperación errores | Difícil               | **Fácil (reprocesar)**       |
| Debugging            | Difícil               | **Fácil (JSON guardado)**    |
| Escalabilidad        | Limitada              | **Alta (queue_job)**         |

## 📦 Dependencias

- `queue_job` (OCA) - Para procesamiento asíncrono
- `sale_management` - Gestión de ventas
- `stock` - Gestión de inventario

## 🛠️ Instalación

1. Instalar dependencia OCA:
```bash
pip install odoo-addon-queue_job
```

2. Agregar al `addons_path` de Odoo

3. Actualizar lista de módulos e instalar

## ⚙️ Configuración

1. Ir a **MercadoLibre Async > Configuración**
2. Completar credenciales de ML:
   - Client ID
   - Client Secret
   - Seller ID
   - Access Token / Refresh Token
3. Configurar intervalos y opciones

## 📋 Modelos

### `meli.order.raw`
Tabla staging para almacenar órdenes crudas.

| Campo           | Descripción                          |
| --------------- | ------------------------------------ |
| order_id_ml     | ID único de la orden en ML           |
| json_data       | JSON crudo de la API                 |
| state           | pending/processing/done/error        |
| error_message   | Detalle del error si falló           |
| retry_count     | Cantidad de reintentos               |
| sale_order_id   | Orden de venta creada                |

### `meli.async.config`
Configuración singleton del módulo.

## 🔄 Crons

| Cron                    | Intervalo | Descripción                    |
| ----------------------- | --------- | ------------------------------ |
| Extraer Órdenes         | 15 min    | Descarga JSONs de ML           |
| Procesar Órdenes        | 5 min     | Procesa pendientes con jobs    |
| Limpieza                | 1 semana  | Elimina procesados antiguos    |

## 🐛 Debugging

1. Ver órdenes con error: **MercadoLibre Async > Órdenes Raw** (filtro "Con Error")
2. Ver JSON original: Botón "Ver JSON" en el formulario
3. Reprocesar: Botón "Reprocesar" en órdenes con error

## 📝 Notas

- El JSON original siempre queda guardado para auditoría
- Los reintentos son automáticos (configurable, default 3)
- Las órdenes procesadas se limpian después de 30 días

## 👤 Autor

Hitofusion - https://www.hitofusion.com

## 📄 Licencia

LGPL-3
