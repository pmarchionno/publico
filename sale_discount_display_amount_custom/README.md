# Sale Discount Display Amount

**Versión corregida para Odoo 17** por Hito Fusion

## Descripción

Este módulo muestra el monto del descuento calculado tanto a nivel de línea de pedido como a nivel de pedido de venta.

## Correcciones aplicadas (v17.0.1.1.2)

### 1. Hooks corregidos
- **Problema original:** Los hooks `pre_init_hook` y `post_init_hook` usaban `env` como parámetro, pero en Odoo 17 la firma es diferente.
- **Solución:** 
  - `pre_init_hook(cr)` - solo recibe el cursor
  - `post_init_hook(cr, registry)` - recibe cursor y registry
  - Se crea el environment manualmente cuando se necesita ORM

### 2. Vistas XML corregidas
- **Problema original:** La vista `sale_order_view_form_display_discount` tenía XML mal estructurado con `position="attributes"` sin atributos válidos.
- **Solución:** Se reescribió la vista para agregar los campos de descuento de forma correcta después de `tax_totals`.

### 3. Compatibilidad con Odoo 17
- XPath actualizado de `//tree` a `//list` en la vista de líneas
- Settings ubicados en los XPath correctos para la estructura de v17

## Campos añadidos

### En sale.order:
- `discount_total` - Descuento total (con impuestos)
- `discount_subtotal` - Descuento subtotal (sin impuestos)
- `price_subtotal_no_discount` - Subtotal sin descuento
- `price_total_no_discount` - Total sin descuento

### En sale.order.line:
- Los mismos campos a nivel de línea

### En res.company / res.config.settings:
- `display_discount_with_tax` - Mostrar descuento con IVA
- `report_total_without_discount` - Mostrar total sin descuento en reportes

## Dependencias

- `sale_management`

## Autor original

- ACSONE SA/NV
- Odoo Community Association (OCA)

## Correcciones

- Hito Fusion (2026)

## Licencia

AGPL-3.0 or later
