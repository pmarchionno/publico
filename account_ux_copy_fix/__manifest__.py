{
    'name': 'Account UX Copy Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix error when creating debit notes with copy_lines enabled',
    'description': '''
Fix para error "Registro faltante" al crear Notas de Débito
===========================================================

Problema:
---------
Al crear una Nota de Débito desde una Nota de Crédito con la opción 
"Copiar líneas" habilitada, aparece el error:

"El registro no existe o fue eliminado (Registro: account.move.line(XXXXX,))"

Causa:
------
El módulo account_ux de ingadhoc intenta limpiar impuestos inactivos 
de las líneas copiadas, pero durante el proceso de copy() algunas líneas 
son eliminadas y recreadas por _sync_dynamic_lines(), causando referencias
huérfanas.

Solución:
---------
Este módulo sobreescribe el método copy() para verificar que las líneas
existan antes de intentar modificarlas.
    ''',
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'installable': True,
    'auto_install': False,
}
