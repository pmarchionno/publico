# -*- coding: utf-8 -*-
{
    'name': 'MercadoLibre Orders - Optimized Cron (Alto Volumen)',
    'version': '17.0.2.0.0',
    'summary': 'Optimización del cron de ML para ALTO VOLUMEN (1k-3k órdenes/día)',
    'description': """
MercadoLibre Orders - Optimized Cron (Alto Volumen)
====================================================

Versión optimizada para operaciones de alto volumen en Odoo.sh.

Configuración por defecto (Alto Volumen):
-----------------------------------------
* Batch size: 100 órdenes por ejecución
* Tiempo máximo: 240 segundos (4 minutos)
* Órdenes por página: 50 (máximo de ML API)

Capacidad con cron cada 30 min:
-------------------------------
* 2 ejecuciones/hora × 100 = 200 órdenes/hora
* Soporta hasta 4.800 órdenes/día

Características:
----------------
* Procesamiento por lotes (batch) con límite configurable
* Control de tiempo de ejecución máximo
* Evita commits manuales dentro de loops
* Paginación inteligente con estado persistente
* Compatible con queue_job para procesamiento asíncrono (opcional)
* Logging mejorado para diagnóstico

Cambios v2.0.0:
---------------
* Defaults optimizados para alto volumen
* batch_size: 50 → 100
* max_time: 180s → 240s

Autor: Hito
    """,
    'author': 'Hito',
    'website': 'https://www.hitofusion.com',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': [
        'meli_oerp_multiple',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'views/connection_configuration_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
