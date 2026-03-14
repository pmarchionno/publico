# -*- coding: utf-8 -*-
{
    "name": "Purchase Price No Round",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "Evita el redondeo prematuro del precio en líneas de compra",
    "description": """
Purchase Price No Round
=======================

Este módulo corrige el comportamiento de Odoo que redondea el precio unitario
a 2 decimales cuando se carga desde la lista de precios del proveedor.

**Problema resuelto:**
- Precio en supplierinfo: 2686.0697
- Precio en PO line (antes): 2686.07 (redondeado)
- Precio en PO line (después): 2686.0697 (completo)

**Cambios técnicos:**
- Override de `_compute_price_unit_and_date_planned_and_name` con depends completos
- Eliminación del `float_round()` que causaba el redondeo prematuro
- Usa precisión decimal de 'Product Price' para mantener todos los decimales

**Ticket:** TK#2026/03157
    """,
    "author": "Hito",
    "website": "https://www.hitofusion.com",
    "license": "LGPL-3",
    "depends": [
        "purchase",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
