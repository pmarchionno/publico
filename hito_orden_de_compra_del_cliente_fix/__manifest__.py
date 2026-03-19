{
    "name": "Hito - Fix Remitos Duplicados",
    "version": "18.0.1.0.0",
    "category": "Stock",
    "summary": "Fix para evitar generación de remitos duplicados en entregas parciales",
    "description": """
Fix para el módulo hito_orden_de_compra_del_cliente

PROBLEMA:
El método button_validate() llamaba a assign_numbers() duplicando la asignación
que ya hace stock_voucher en _action_done().

SOLUCIÓN:
Se eliminó la llamada duplicada a assign_numbers() manteniendo solo la validación
de que exista un libro de remitos.

Fecha: 2026-03-19
Autor: Jinzo (Hitofusion)
    """,
    "author": "Hitofusion",
    "website": "https://www.hitofusion.com",
    "depends": ["stock_voucher", "hito_orden_de_compra_del_cliente"],
    "data": [],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
