# HR Expense Custom - Payment Bundle Support

## Descripción

Extensiones para el wizard de pago de gastos (`account.payment.register`) que agregan:

1. **Talonario de Recibo**: Campo `receiptbook_id` visible al pagar gastos
2. **Pagos Múltiples**: Soporte para el método `payment_bundle` con líneas de pago

## Funcionalidades

### 1. Talonario de Recibo

Cuando se paga un gasto desde el wizard:
- Se muestra el campo "Talonario de Recibo" después del diario
- Se auto-selecciona el talonario por defecto según el diario
- El talonario se propaga al pago creado

### 2. Pagos Múltiples (Payment Bundle)

Cuando se selecciona un diario con método de pago "Pago Multiple" (`payment_bundle`):

```
┌─────────────────────────────────────────────────────────────┐
│  Registrar Pago de Gasto                                    │
├─────────────────────────────────────────────────────────────┤
│  Diario: [Pagos Múltiples ▼]                                │
│  Método de Pago: Pago Multiple (auto)                       │
│  Talonario: [____________ ▼]                                │
├─────────────────────────────────────────────────────────────┤
│  ═══════════════ Líneas de Pago ═══════════════             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Diario    │ Método    │ Monto   │ Talonario         │   │
│  │ Banco A   │ Transf.   │ 5000    │ T-001             │   │
│  │ Efectivo  │ Manual    │ 3000    │ T-002             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Total en líneas: 8000    Diferencia: 0 ✓                   │
└─────────────────────────────────────────────────────────────┘
```

Al confirmar:
- Se crea un **pago principal** con `amount=0` y `is_main_payment=True`
- Se crean **pagos hijos** (`link_payment_ids`) para cada línea
- Todos los pagos se vinculan y se postean juntos

## Dependencias

### Requeridas
- `hr_expense` (Odoo base)
- `account_payment_pro_receiptbook` (ADHOC)

### Opcionales
- `l10n_ar_payment_bundle` (ADHOC) - Para la funcionalidad de pagos múltiples

## Instalación

1. Copiar el módulo a la carpeta de addons
2. Actualizar lista de aplicaciones
3. Instalar "HR Expense Custom - Payment Bundle Support"

## Configuración

### Para Pagos Múltiples

1. Ir a **Contabilidad → Configuración → Diarios**
2. Crear un diario de tipo "Efectivo" llamado "Pagos Múltiples"
3. En pestaña "Pagos salientes", agregar el método "Pago Multiple"
4. En pestaña "Pagos entrantes", agregar el método "Pago Multiple"

### Para Talonarios

1. Ir a **Contabilidad → Configuración → Talonarios de Pago**
2. Crear talonarios asociados a cada diario de pago

## Compatibilidad

- **Odoo**: 18.0
- **Python**: 3.10+

## Autor

**Hito** - https://www.hito.com.ar

## Licencia

LGPL-3
