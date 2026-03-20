{
    "name": "Stock Voucher Fix - Food Novelty",
    "version": "18.0.1.0.0",
    "category": "Stock",
    "summary": "Fixes para stock_voucher: wizard backorder y cierre de modal",
    "description": """
Stock Voucher Fix - Food Novelty
================================

Fixes aplicados:

1. **stock_backorder_confirmation.py**
   - Corregido método process() que devolvía tupla (res, print_action)
   - Ahora devuelve solo la acción de impresión

2. **stock_picking.py - do_print_voucher()**
   - Agregado close_on_report_download = True
   - El wizard se cierra automáticamente al descargar el PDF

Ticket: Food Novelty - Remitos duplicados y wizard abierto
Fecha: 2026-03-20
    """,
    "author": "Hitofusion",
    "website": "https://www.hitofusion.com",
    "license": "LGPL-3",
    "depends": ["stock_voucher"],
    "data": [],
    "installable": True,
    "auto_install": False,
}
