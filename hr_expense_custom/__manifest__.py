# -*- coding: utf-8 -*-
{
    'name': 'HR Expense - Talonario de Recibo',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Agrega selección de Talonario de Recibo al pago de gastos',
    'description': """
HR Expense - Talonario de Recibo
================================

Este módulo agrega la funcionalidad de seleccionar un **Talonario de Recibo** 
al registrar pagos desde Reportes de Gastos, replicando el comportamiento 
disponible en "Pagos de Proveedores" del módulo account_payment_pro_receiptbook.

Características:
----------------
* Campo "Talonario de Recibo" en el wizard de registro de pago desde gastos
* Filtro automático por tipo de talonario (recibo de pago)
* El talonario seleccionado se propaga al pago creado

Dependencias:
-------------
* hr_expense
* account
* account_payment_pro_receiptbook
    """,
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'account',
        'account_payment_pro_receiptbook',
    ],
    'data': [
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}