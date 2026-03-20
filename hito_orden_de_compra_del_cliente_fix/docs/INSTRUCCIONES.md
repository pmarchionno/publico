# Instrucciones para aplicar el fix

## Problema
El módulo `hito_orden_de_compra_del_cliente` tiene un override de `button_validate()` 
que causa remitos duplicados y bloqueo del wizard.

## Solución
Reemplazar el archivo `models/stock_picking.py` del módulo original con el contenido de
`stock_picking_FIXED.py` incluido en este paquete.

## Pasos

### Opción 1: Modificar directamente en el servidor
```bash
# Conectar por SSH al servidor
ssh usuario@servidor

# Ir al directorio del módulo
cd /ruta/addons/hito_orden_de_compra_del_cliente/models/

# Backup del original
cp stock_picking.py stock_picking.py.bak

# Reemplazar con el archivo corregido
# (copiar contenido de docs/stock_picking_FIXED.py)
```

### Opción 2: Via Git
```bash
# En el repositorio del cliente
git checkout -b fix/remitos-duplicados
# Editar hito_orden_de_compra_del_cliente/models/stock_picking.py
# Eliminar el método button_validate() completo
git add .
git commit -m "fix: Eliminar button_validate que causa remitos duplicados"
git push
```

## Verificación
1. Reiniciar Odoo o actualizar el módulo
2. Crear un picking de salida
3. Validar con entrega parcial
4. Verificar que solo se genere 1 remito

## Configuración requerida
En el picking type "Órdenes de entrega":
- Marcar "Talonario requerido" (book_required = True)
- Asignar talonario por defecto

---
Fix por Hitofusion - 2026-03-20
