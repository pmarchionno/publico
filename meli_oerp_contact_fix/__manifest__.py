{
    'name': 'Meli OERP Contact Fix',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Soluciona la jerarquía y creación de contactos de facturación en órdenes de MercadoLibre',
    'description': """
    Módulo para corregir el comportamiento de meli_oerp al crear/actualizar contactos:
    - Asegura que el contacto principal y el de factura se creen como individuos (company_type = 'person').
    - Evita que Odoo rompa el vínculo parent_id por restricciones de compañía.
    - Asegura que el nombre (Razón Social) y CUIT de facturación no se pierdan.
    """,
    'author': 'Custom',
    'depends': ['base', 'meli_oerp'],
    'data': [],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
