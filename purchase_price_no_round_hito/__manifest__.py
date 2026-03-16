# -*- coding: utf-8 -*-
{
    "name": "Purchase Price No Round (Hito)",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "Evita el redondeo prematuro del precio en lineas de compra",
    "description": """
Purchase Price No Round (Hito)
==============================

Modulo propio de Hitofusion basado en purchase_price_no_round.

Este modulo corrige el comportamiento de Odoo que redondea el precio unitario
a 2 decimales cuando se carga desde la lista de precios del proveedor.

**Mejoras sobre el modulo original:**
- Integracion nativa con product_replenishment_cost
- Usa net_price (precio con reglas de costo de reposicion) cuando esta disponible
- Mantiene precision completa sin redondeo

**Problema resuelto:**
- Precio en supplierinfo: 2686.0697
- Precio en PO line (antes): 2686.07 (redondeado)
- Precio en PO line (despues): 2686.0697 (completo)

**Ticket:** TK#2026/03157
    """,
    "author": "Hitofusion",
    "website": "https://www.hitofusion.com",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "product_replenishment_cost",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
