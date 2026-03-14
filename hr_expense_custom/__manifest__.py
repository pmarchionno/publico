# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Custom - Payment Bundle Support',
    'version': '18.0.2.4.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Talonario de Recibo y Pagos Múltiples en wizard de pago de gastos',
    'description': '''
        Extensiones para el wizard de registro de pago (account.payment.register):
        
        1. Talonario de Recibo:
           - Define el campo receiptbook_id en el wizard (no viene de otro módulo)
           - Auto-selecciona el talonario por defecto según el diario
           - Propaga el talonario al pago creado
        
        2. Pagos Múltiples (Payment Bundle):
           - Detecta cuando el método de pago es "payment_bundle"
           - Agrega una pestaña de líneas de pago con diferentes diarios
           - Cada línea puede tener su propio diario, monto y talonario
           - Al confirmar, crea un pago principal + pagos hijos vinculados
        
        Requiere:
        - hr_expense (para contexto de gastos)
        - account_payment_pro_receiptbook (para el modelo account.payment.receiptbook)
        
        Opcional:
        - l10n_ar_payment_bundle (para pagos múltiples con link_payment_ids)
    ''',
    'author': 'Hito',
    'website': 'https://www.hito.com.ar',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'account',
        'account_payment_pro_receiptbook',  # Para el modelo account.payment.receiptbook
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
