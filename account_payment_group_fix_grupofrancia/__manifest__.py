# -*- coding: utf-8 -*-
{
    'name': 'Account Payment Group Fix - Grupo Francia',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix para recálculo en tiempo real de Deuda Seleccionada',
    'description': '''
        Soluciona el problema donde el campo "Deuda Seleccionada" no se actualiza
        automáticamente al eliminar líneas de comprobantes en la pestaña Deudas.
        
        Cambios implementados:
        - selected_debt: store=False para forzar recálculo en tiempo real
        - Agrega onchange para actualización inmediata en la interfaz
    ''',
    'author': 'Hitofusion - Jinzo',
    'depends': [
        'account_payment_group',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
