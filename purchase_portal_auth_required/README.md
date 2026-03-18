# Purchase Portal Authentication Required

## Descripción

Este módulo mejora la seguridad del acceso a órdenes de compra en el portal de Odoo.

## Problema

Cuando se envía una orden de compra por email, Odoo incluye un botón "Ver orden" con un `access_token` en la URL. Esto permite que cualquier persona con el link pueda ver la orden sin necesidad de autenticarse, lo cual representa un riesgo de seguridad.

## Solución

Este módulo:

1. **Requiere autenticación** para ver órdenes de compra en el portal
2. **Ignora el access_token** - ya no permite acceso sin login
3. **Redirige al login** si el usuario no está autenticado

## Instalación

1. Copiar el módulo a la carpeta de addons
2. Actualizar la lista de módulos
3. Instalar "Purchase Portal Authentication Required"

## Consideraciones

Después de instalar este módulo:

- Los proveedores necesitarán tener una cuenta de portal
- Deberán iniciar sesión para ver sus órdenes de compra
- Los links con access_token en emails anteriores dejarán de funcionar sin login

## Compatibilidad

- Odoo 17.0

## Autor

Hitofusion - https://www.hitofusion.com

## Licencia

LGPL-3
