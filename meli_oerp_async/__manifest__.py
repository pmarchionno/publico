# -*- coding: utf-8 -*-
{
    'name': 'MercadoLibre Async ETL',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Sincronización asíncrona de órdenes de MercadoLibre con arquitectura ETL',
    'description': '''
        Módulo de sincronización de MercadoLibre con arquitectura ETL:
        
        FASE 1 - EXTRACCIÓN (Cron cada 15-30 min):
        - GET /orders/search con paginación
        - Guardar JSONs en tabla staging (meli.order.raw)
        - Sin procesamiento, solo descarga
        
        FASE 2 - PROCESAMIENTO (Async con queue_job):
        - Leer de meli.order.raw
        - Crear/actualizar sale.order, stock.picking, etc.
        - Marcar como procesado
        - Reintentos automáticos si falla
        
        Ventajas:
        - Sin timeouts (extracción rápida)
        - Reprocesable (JSON ya guardado)
        - Auditable (JSON original guardado)
        - Escalable (procesar en paralelo)
        - Debugging fácil
    ''',
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_management',
        'stock',
        'queue_job',  # OCA queue_job para procesamiento async
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/meli_order_raw_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
