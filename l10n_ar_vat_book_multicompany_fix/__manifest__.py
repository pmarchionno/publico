# -*- coding: utf-8 -*-
{
    'name': 'Argentina VAT Book Multi-Company Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations/Reporting',
    'summary': 'Corrige el filtro multi-company en el Libro de IVA (ZIP)',
    'description': """
Argentina VAT Book Multi-Company Fix
====================================

Este módulo corrige el comportamiento del reporte Libro de IVA (ZIP) para que
incluya todos los comprobantes de las empresas seleccionadas en el filtro,
alineándose con la lógica del botón XLSX que ya funciona correctamente.

**Problema:**
El método `_vat_book_get_lines_domain` usaba `self.env.company.ids` que solo
devuelve la compañía actual del usuario, ignorando las compañías seleccionadas
en el filtro del reporte.

**Solución:**
Se modifica para obtener las compañías desde `options['companies']`, igual que
hace el reporte XLSX.

**Archivo corregido:** l10n_ar_reports/models/l10n_ar_vat_book.py
**Método:** _vat_book_get_lines_domain
    """,
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': [
        'l10n_ar_reports',
    ],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
