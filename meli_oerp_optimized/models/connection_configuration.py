# -*- coding: utf-8 -*-
from odoo import fields, models


class MercadoLibreConnectionConfiguration(models.Model):
    _inherit = 'mercadolibre.configuration'

    # Configuración de optimización del cron - ALTO VOLUMEN (1k-3k órdenes/día)
    mercadolibre_cron_batch_size = fields.Integer(
        string='Tamaño de lote (órdenes)',
        default=100,  # Optimizado: 100 en vez de 50
        help='Cantidad máxima de órdenes a procesar por ejecución del cron. '
             'Para alto volumen (1k-3k/día): usar 100-150'
    )
    
    mercadolibre_cron_max_time = fields.Integer(
        string='Tiempo máximo (segundos)',
        default=240,  # Optimizado: 4 minutos
        help='Tiempo máximo de ejecución del cron antes de detenerse. '
             'En Odoo.sh el timeout es ~5 minutos, usamos 240s (4 min).'
    )
    
    mercadolibre_cron_use_queue = fields.Boolean(
        string='Usar Queue Job',
        default=False,
        help='Si está instalado queue_job, procesar órdenes de forma asíncrona. '
             'Mejora rendimiento pero requiere el módulo OCA queue_job.'
    )
    
    mercadolibre_cron_last_offset = fields.Integer(
        string='Último offset procesado',
        default=0,
        help='Offset de la última página procesada. Se resetea al llegar al final.'
    )
    
    mercadolibre_cron_orders_per_page = fields.Integer(
        string='Órdenes por página API',
        default=50,  # Máximo de ML API
        help='Cantidad de órdenes a solicitar por llamada a la API de ML. '
             'Máximo permitido por ML: 50'
    )
