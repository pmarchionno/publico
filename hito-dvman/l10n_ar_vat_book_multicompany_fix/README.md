# Argentina VAT Book Multi-Company Fix

## Problema

El reporte **Libro de IVA (ZIP)** en `Contabilidad → Reportes → Declaración Fiscal → Libro de IVA` no respetaba el filtro multi-company. Solo mostraba comprobantes de la compañía actual del usuario, ignorando las compañías seleccionadas en el filtro.

El botón **XLSX** funcionaba correctamente con multi-company.

## Causa Raíz

En el archivo `/enterprise/l10n_ar_reports/models/l10n_ar_vat_book.py`, el método `_vat_book_get_lines_domain` usaba:

```python
company_ids = self.env.company.ids  # ❌ Solo compañía actual
```

Mientras que el reporte XLSX usa `options['companies']` que contiene las compañías seleccionadas en el filtro.

## Solución

Este módulo sobrescribe el método para obtener las compañías desde `options['companies']`:

```python
company_ids = [comp['id'] for comp in options.get('companies', [])] or self.env.company.ids
```

## Instalación

1. Copiar el módulo a `/src/usr/internal-addons/`
2. Actualizar lista de aplicaciones
3. Instalar "Argentina VAT Book Multi-Company Fix"

## Compatibilidad

- Odoo 17.0 Enterprise
- Requiere: `l10n_ar_reports`

## Autor

Hitofusion - https://www.hitofusion.com

## Fecha

2026-03-23
