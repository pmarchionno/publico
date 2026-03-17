# -*- coding: utf-8 -*-
{
    'name': 'Fix Recibo de Pago - Retenciones Argentina',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Corrige el importe de transferencia en recibos con retenciones',
    'description': '''
        Corrige un bug en el reporte de recibo de pago cuando hay retenciones.
        
        PROBLEMA:
        En pagos simples con retenciones, la línea de transferencia mostraba 
        el total del pago (incluyendo retenciones) en lugar del monto neto.
        
        SOLUCIÓN:
        Usa el campo amount del pago (monto neto) para la línea de transferencia.
    ''',
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': [
        'l10n_ar_tax',
    ],
    'data': [
        'report/payment_receipt_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
