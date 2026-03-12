# HR Expense - Talonario de Recibo

**Versión:** 18.0.1.0.0  
**Autor:** Hitofusion  
**Licencia:** LGPL-3

## Descripción

Módulo custom para Odoo 18 que agrega la funcionalidad de seleccionar un **Talonario de Recibo** (Receipt Book) al registrar pagos desde Reportes de Gastos (HR Expense).

### Características

- ✅ Campo "Talonario de Recibo" en el wizard de registro de pago desde gastos
- ✅ Mismo comportamiento que en "Pagos de Proveedores" de Contabilidad
- ✅ Propagación automática del talonario al pago creado
- ✅ Autocompletar talonario por defecto del diario
- ✅ Compatible con Odoo 18 Community y Enterprise
- ✅ Sin dependencias de módulos externos

## Dependencias

- `hr_expense` (módulo core)
- `account` (módulo core)

## Instalación

### Método 1: Descarga manual

1. Descargar la carpeta `hr_expense_custom`
2. Colocar en el directorio de addons personalizados de tu Odoo (ej: `/addons` o `/cl-emu-custom`)
3. Ir a **Aplicaciones** → **Actualizar lista de aplicaciones** (modo desarrollador activado)
4. Buscar "HR Expense - Talonario de Recibo"
5. Click en **Instalar**

### Método 2: CLI Odoo

```bash
odoo -u hr_expense_custom -d nombre_basedatos
```

### Método 3: Interfaz web

1. Ir a **Configuración** → **Apps & Modules** → **Apps**
2. Activar modo desarrollador (Configuración → Activar el Modo Desarrollador)
3. Click en **Actualizar lista de aplicaciones**
4. Buscar "HR Expense - Talonario de Recibo"
5. Click en **Instalar**

## Uso

1. Abrir un **Reporte de Gastos** (HR → Gastos → Reportes)
2. Registrar Pago
3. En el wizard de pago, el campo **"Talonario de Recibo"** aparecerá automáticamente después del diario
4. Seleccionar el talonario deseado
5. Completar el registro de pago

El talonario seleccionado se propagará automáticamente al pago creado.

## Contenido del módulo

```
hr_expense_custom/
├── __manifest__.py              # Definición del módulo
├── __init__.py                  # Inicializador
├── README.md                    # Este archivo
├── models/
│   ├── __init__.py             # Importa el modelo
│   └── account_payment_register.py  # Lógica principal
└── views/
    └── account_payment_register_views.xml  # Interfaz XML
```

## Funcionalidad técnica

### Modelo extendido: `account.payment.register`

#### Campo agregado:

- **receiptbook_id** (Many2one → account.payment.receiptbook)
  - String: "Talonario de Recibo"
  - Sin permitir crear ni abrir registros en línea

#### Métodos sobrescritos:

1. **default_get()**
   - Autodetecta si el wizard es abierto desde Gastos
   - Busca y asigna talonario por defecto del diario
   - Compatible con variantes del modelo receiptbook

2. **\_create_payment_vals_from_wizard()**
   - Propaga receiptbook_id al pago creado
   - Verifica que receiptbook_id exista en account.payment antes de propagarlo

3. **\_compute_is_from_expense()**
   - Campo compute para detectar origen del pago
   - Usado internamente para lógica condicional

## Cambios de versión

### v18.0.1.0.0 (inicial)

- Implementación base del módulo
- Agregación de campo receiptbook_id al wizard
- Propagación al pago creado
- Vista XML integrada

## Soporte

Para reportar bugs o solicitar mejoras, contactar a Hitofusion.

---

**Última actualización:** 12 de marzo de 2026
