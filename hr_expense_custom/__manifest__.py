# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Custom - Payment Bundle Support',
    'version': '18.0.2.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Talonario de Recibo y Pagos Múltiples en wizard de pago de gastos',
    'description': '''
        Extensiones para el módulo de Gastos (hr_expense):
        
        1. Talonario de Recibo:
           - Agrega el campo receiptbook_id al wizard de registro de pago
           - Auto-selecciona el talonario por defecto según el diario
           - Propaga el talonario al pago creado
        
        2. Pagos Múltiples (Payment Bundle):
           - Permite usar el método "Pago Multiple" desde gastos
           - Agrega una pestaña de líneas de pago con diferentes diarios
           - Cada línea puede tener su propio diario, monto y talonario
           - Al confirmar, crea un pago principal + pagos hijos vinculados
        
        Requiere:
        - account_payment_pro (para receiptbook_id)
        - l10n_ar_payment_bundle (para pagos múltiples)
    ''',
    'author': 'Hito',
    'website': 'https://www.hito.com.ar',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'account',
        'account_payment_pro_receiptbook',
        # l10n_ar_payment_bundle es opcional - si no está instalado,
        # la funcionalidad de pagos múltiples no estará disponible
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
