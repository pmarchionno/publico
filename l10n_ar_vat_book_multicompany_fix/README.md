# Argentina VAT Book Multi-Company Fix

## Compatibilidad

- **Odoo 18.0** Enterprise
- Requiere: `l10n_ar_reports`

## Problema

El reporte **Libro de IVA (ZIP)** no respetaba el filtro multi-company.

## Solución

Sobrescribe `_vat_book_get_lines_domain` para usar `options['companies']`.

## Autor

Hitofusion - 2026-03-23
