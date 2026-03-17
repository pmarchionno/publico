# 📊 Análisis de Escalabilidad MeLi → Odoo

**Objetivo:** Procesar más de 10,000 ventas de MercadoLibre sin interrupciones de cron  
**Fecha:** Marzo 2026  
**Preparado por:** Hitofusion

---

## 🔍 Diagnóstico del Estado Actual

El módulo `meli_oerp_async` implementa ETL con `queue_job`, pero presenta cuellos de botella al escalar:

| Problema | Causa | Impacto |
|----------|-------|---------|
| Cron de extracción único | Un solo proceso descarga todo | Timeout en volúmenes altos |
| Jobs 1:1 por orden | 10,000 órdenes = 10,000 jobs individuales | Saturación de cola |
| Sin rate limiting | Odoo crea más rápido de lo que puede commitear | Memory leak → kill |
| Sin checkpoints | Si falla a mitad, recomienza todo | Tiempo perdido |
| Transacciones largas | Un job = toda la orden | Lock contention en BD |

---

## 🛠️ Alternativas Propuestas

### OPCIÓN A: Micro-Batching con Control de Flujo
*Mejora evolutiva del módulo actual*

**Concepto:** Procesar en micro-lotes de 50-100 órdenes con commits intermedios y pausa controlada.

| Aspecto | Valor |
|---------|-------|
| **Complejidad** | ⭐⭐ Baja |
| **Impacto** | ⭐⭐⭐ Medio-Alto |
| **Escalabilidad** | Hasta ~20,000 órdenes |
| **Mantenimiento** | Fácil, código simple |
| **Tiempo impl.** | 2-4 horas |

✅ **Pros:** Fácil de implementar, no requiere infraestructura nueva  
❌ **Contras:** No paraleliza, sigue siendo secuencial

---

### OPCIÓN B: Workers Paralelos con Queue Job
*Optimización de la arquitectura actual*

**Concepto:** Usar múltiples channels de queue_job con workers dedicados y chunking inteligente.

| Aspecto | Valor |
|---------|-------|
| **Complejidad** | ⭐⭐⭐ Media |
| **Impacto** | ⭐⭐⭐⭐ Alto |
| **Escalabilidad** | Hasta ~50,000 órdenes |
| **Mantenimiento** | Requiere monitoreo de workers |
| **Tiempo impl.** | 4-8 horas |

✅ **Pros:** Aprovecha infraestructura existente (queue_job), paralelismo real  
❌ **Contras:** Requiere tunear workers y memoria

---

### OPCIÓN C: Procesamiento en Fases con Cursor Server-Side
*Approach profesional de alto volumen*

**Concepto:** Separar en 3 fases con cursores server-side de PostgreSQL para evitar cargar todo en memoria.

| Aspecto | Valor |
|---------|-------|
| **Complejidad** | ⭐⭐⭐⭐ Alta |
| **Impacto** | ⭐⭐⭐⭐⭐ Muy Alto |
| **Escalabilidad** | 100,000+ órdenes |
| **Mantenimiento** | Requiere expertise |
| **Tiempo impl.** | 1-2 días |

✅ **Pros:** Escala masivamente, memoria constante, profesional  
❌ **Contras:** Más complejo, requiere testing exhaustivo

---

### OPCIÓN D: Microservicio Externo (Python puro + API)
*Desacoplamiento total*

**Concepto:** Mover extracción y pre-procesamiento a un servicio Python externo que solo llama API de Odoo para crear.

| Aspecto | Valor |
|---------|-------|
| **Complejidad** | ⭐⭐⭐⭐⭐ Muy Alta |
| **Impacto** | ⭐⭐⭐⭐⭐ Máximo |
| **Escalabilidad** | Ilimitada (horizontal) |
| **Mantenimiento** | Requiere DevOps |
| **Tiempo impl.** | 1-2 semanas |

✅ **Pros:** Escala infinitamente, Odoo solo hace lo mínimo  
❌ **Contras:** Infraestructura adicional, más piezas móviles

---

## 📋 Matriz Comparativa

| Criterio | Opción A | Opción B | Opción C | Opción D |
|----------|----------|----------|----------|----------|
| **Volumen máx** | 20K | 50K | 100K+ | ∞ |
| **Tiempo impl** | 4h | 8h | 2d | 2w |
| **Costo infra** | $0 | $0 | $0 | $$$ |
| **Riesgo** | Bajo | Medio | Medio | Alto |
| **Odoo.sh compatible** | ✅ | ✅ | ✅ | ⚠️ |

---

## ✅ Recomendación

**Para producción inmediata: Opción A + B combinadas**

1. Implementar micro-batching (A) como fix rápido
2. Optimizar queue_job channels (B) en paralelo
3. Si sigue sin alcanzar → evaluar Opción C

---

## 💻 Código Sugerido (Opción A+B)

```python
MICRO_BATCH_SIZE = 50
CHUNK_SIZE = 100
PAUSE_BETWEEN_BATCHES = 2  # segundos

@api.model
def cron_process_orders_optimized(self):
    """
    Procesamiento optimizado para alto volumen.
    - Micro-batches con commits
    - Chunks para queue_job
    - Rate limiting incorporado
    """
    config = self.env['meli.async.config'].get_config()
    
    # Contar pendientes
    total_pending = self.env['meli.order.raw'].search_count([
        ('state', '=', 'pending')
    ])
    
    if total_pending == 0:
        return 0
    
    _logger.info(f"MeLi Optimized: {total_pending} órdenes pendientes")
    
    # Si son pocas, procesar directo
    if total_pending <= MICRO_BATCH_SIZE:
        return self._process_micro_batch_sync()
    
    # Si son muchas, encolar por chunks
    pending_ids = self.env['meli.order.raw'].search([
        ('state', '=', 'pending')
    ], order='extracted_at asc').ids
    
    chunks = list(self._chunks(pending_ids, CHUNK_SIZE))
    
    for i, chunk in enumerate(chunks):
        self.with_delay(
            channel='root.meli',
            priority=10 + i,
            description=f"Chunk {i+1}/{len(chunks)} ({len(chunk)} órdenes)"
        )._process_chunk_with_pause(chunk)
    
    return total_pending

def _process_micro_batch_sync(self):
    """Procesamiento síncrono para lotes pequeños."""
    orders = self.env['meli.order.raw'].search([
        ('state', '=', 'pending')
    ], limit=MICRO_BATCH_SIZE, order='extracted_at asc')
    
    processed = 0
    for order in orders:
        try:
            self._process_single_order(order.id)
            processed += 1
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            order.write({
                'state': 'error',
                'error_message': str(e)
            })
            self.env.cr.commit()
    
    return processed

@job(default_channel='root.meli')
def _process_chunk_with_pause(self, order_ids):
    """Procesa un chunk con pausa y commits intermedios."""
    import time
    
    for i, order_id in enumerate(order_ids):
        try:
            self._process_single_order(order_id)
            self.env.cr.commit()
            
            # Pausa cada N órdenes
            if (i + 1) % 10 == 0:
                time.sleep(0.5)
                
        except Exception as e:
            self.env.cr.rollback()
            self.env['meli.order.raw'].browse(order_id).write({
                'state': 'error', 
                'error_message': str(e)
            })
            self.env.cr.commit()
    
    return len(order_ids)

@staticmethod
def _chunks(lst, n):
    """Divide lista en chunks de tamaño n."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
```

---

**Hitofusion** - Consultoría Odoo  
www.hitofusion.com
