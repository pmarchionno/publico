# Account Payment Group Fix - Grupo Francia

## Problema
El campo "Deuda Seleccionada" no se actualiza en tiempo real cuando se eliminan manualmente comprobantes de la pestaña "Deudas".

## Solución
Este módulo fuerza el recálculo del campo `selected_debt` en tiempo real al establecer `store=False`.

## Instalación

1. Copiar esta carpeta a: `/opt/odoo/addons/` (o el directorio de addons custom)
2. Reiniciar Odoo: `service odoo restart`
3. Actualizar lista de aplicaciones: Apps → Update Apps List
4. Buscar: "Account Payment Group Fix Grupo Francia"
5. Instalar el módulo

## Estructura
```
account_payment_group_fix_grupofrancia/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── account_payment_group.py
└── README.md
```
