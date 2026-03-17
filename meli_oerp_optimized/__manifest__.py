# -*- coding: utf-8 -*-
{
    'name': 'MercadoLibre Orders - Optimized Cron',
    'version': '17.0.1.0.0',
    'summary': 'Optimización del cron de órdenes de MercadoLibre para Odoo.sh',
    'description': """
MercadoLibre Orders - Optimized Cron
====================================

Optimiza el procesamiento de órdenes de MercadoLibre para evitar timeouts 
y problemas de rendimiento en Odoo.sh.

Características:
----------------
* Procesamiento por lotes (batch) con límite configurable
* Control de tiempo de ejecución máximo
* Evita commits manuales dentro de loops
* Paginación inteligente con estado persistente
* Compatible con queue_job para procesamiento asíncrono (opcional)
* Logging mejorado para diagnóstico

Configuración:
--------------
* mercadolibre_cron_batch_size: Órdenes por ejecución (default: 50)
* mercadolibre_cron_max_time: Tiempo máximo en segundos (default: 180)
* mercadolibre_cron_use_queue: Usar queue_job si está disponible

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