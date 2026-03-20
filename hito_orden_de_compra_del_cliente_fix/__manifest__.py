{
    "name": "Hito - Fix Remitos Duplicados",
    "version": "18.0.2.0.0",
    "category": "Stock",
    "summary": "Fix para evitar generación de remitos duplicados - SIN override de button_validate",
    "description": """
Fix para el módulo hito_orden_de_compra_del_cliente
===================================================

PROBLEMA ORIGINAL:
El método button_validate() en hito_orden_de_compra_del_cliente:
1. Lanzaba ValidationError antes de que stock_voucher pudiera validar
2. Llamaba a assign_numbers() duplicando la asignación de stock_voucher._action_done()

SOLUCIÓN v2.0 (2026-03-20):
Se ELIMINA completamente el override de button_validate() porque:
- stock_voucher.do_stock_voucher_transfer_check() ya valida book_id
- stock_voucher._action_done() ya asigna los números de remito

IMPORTANTE:
Este módulo es solo documentación. El fix real se aplica modificando
directamente hito_orden_de_compra_del_cliente/models/stock_picking.py
para ELIMINAR el método button_validate() completo.

Ver docs/INSTRUCCIONES.md para aplicar el fix.

Fecha: 2026-03-20
Autor: Jinzo (Hitofusion)
Ticket: Food Novelty - Remitos duplicados
    """,
    "author": "Hitofusion",
    "website": "https://www.hitofusion.com",
    "depends": ["stock"],
    "data": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
