# Stock Voucher Fix - Food Novelty

## Problema
1. El wizard de backorder quedaba abierto después de validar
2. Los remitos no se asignaban correctamente

## Solución
Este módulo hereda de `stock_voucher` y corrige:

### 1. Wizard Backorder (`wizards/stock_backorder_confirmation.py`)
- El método `process()` devolvía `(res, print_action)` (tupla)
- Ahora devuelve solo `print_action`

### 2. Impresión de voucher (`models/stock_picking.py`)
- Agregado `close_on_report_download = True`
- El wizard se cierra al descargar el PDF

## Configuración requerida
En el picking type "Órdenes de entrega":
- Marcar "Talonario requerido" (`book_required = True`)
- Asignar talonario por defecto

## Instalación
1. Copiar módulo a la carpeta de addons
2. Actualizar lista de aplicaciones
3. Instalar "Stock Voucher Fix - Food Novelty"

## Autor
Hitofusion - 2026-03-20
