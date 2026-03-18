{
    "name": "Account Terms Fix",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Fix for needed_terms when value is False instead of dict",
    "description": """
Corrige el problema donde el campo needed_terms puede tener valor False 
en lugar de un diccionario, causando errores al acceder como diccionario.

Problema: Al confirmar Ordenes de Pago con retenciones, éstas desaparecen.
Causa: El método _compute_needed_terms no maneja el caso donde needed_terms es False.
Solución: Agregar verificación isinstance antes de acceder a needed_terms como dict.
    """,
    "author": "Hitofusion",
    "website": "https://www.hitofusion.com",
    "depends": ["account"],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
