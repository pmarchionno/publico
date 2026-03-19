{
    "name": "Argentina - Preserve Manual Withholding Amounts",
    "version": "18.0.1.0.0",
    "category": "Localization",
    "summary": "Preserva importes de retenciones editados manualmente en pagos",
    "description": """
Este módulo corrige un problema donde los importes de retenciones editados 
manualmente se pierden al confirmar el pago.

El problema ocurre porque el método _compute_l10n_ar_withholding_line_ids 
usa Command.clear() que borra todas las líneas de retención cada vez que 
se dispara el compute (por cambios en date, partner_id, etc.).

Este módulo:
- Preserva las líneas de retención existentes si el usuario editó el amount
- Solo recrea las líneas si realmente cambió la posición fiscal
- Marca las líneas editadas manualmente con un flag 'manual_amount'
    """,
    "author": "Hitofusion (Jinzo)",
    "website": "https://www.hitofusion.com",
    "license": "LGPL-3",
    "depends": ["l10n_ar_tax"],
    "data": [],
    "installable": True,
    "auto_install": False,
}
