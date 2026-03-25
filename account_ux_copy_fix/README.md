# Account UX Copy Fix

## Problema

Al crear una Nota de Débito desde una Nota de Crédito con la opción "Copiar líneas" habilitada, aparece el error:

```
El registro no existe o fue eliminado.
(Registro: account.move.line(XXXXX,), Usuario: X)
```

## Causa Raíz

El módulo `account_ux` de ingadhoc sobreescribe el método `copy()` de `account.move` para limpiar impuestos inactivos de las líneas copiadas:

```python
def copy(self, default=None):
    res = super().copy(default=default)
    for line_to_clean in res.mapped("line_ids").filtered(...):
        line_to_clean.tax_ids = [...]  # ← FALLA AQUÍ
```

Durante el proceso de `copy()`, Odoo ejecuta `_sync_dynamic_lines()` que puede eliminar y recrear líneas (especialmente las de impuestos y términos de pago). Cuando el código intenta acceder a una línea que fue eliminada, se produce el `MissingError`.

## Solución

Este módulo:

1. Usa `.exists()` para obtener solo las líneas que realmente existen
2. Envuelve la modificación en try/except para manejar casos edge
3. Loguea warnings en lugar de fallar

## Instalación

1. Copiar el módulo a la carpeta de addons
2. Actualizar lista de aplicaciones
3. Instalar "Account UX Copy Fix"

## Compatibilidad

- Odoo 18.0
- Requiere: account (base)
- Compatible con: account_ux (ingadhoc)

## Autor

Hitofusion - https://www.hitofusion.com
