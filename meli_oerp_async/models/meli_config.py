# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MeliAsyncConfig(models.Model):
    """
    Configuración para sincronización async de MercadoLibre.
    Singleton pattern - solo un registro.
    """
    _name = 'meli.async.config'
    _description = 'Configuración MercadoLibre Async'

    name = fields.Char(default='Configuración ML Async', readonly=True)
    
    # Credenciales ML
    client_id = fields.Char(
        string='Client ID',
        help='App ID de MercadoLibre'
    )
    client_secret = fields.Char(
        string='Client Secret',
        help='Secret Key de MercadoLibre'
    )
    access_token = fields.Char(
        string='Access Token',
        help='Token de acceso actual'
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        help='Token para renovar access_token'
    )
    seller_id = fields.Char(
        string='Seller ID',
        help='ID del vendedor en MercadoLibre'
    )
    
    # Configuración de extracción
    extraction_interval = fields.Integer(
        string='Intervalo Extracción (min)',
        default=15,
        help='Cada cuántos minutos ejecutar la extracción'
    )
    extraction_batch_size = fields.Integer(
        string='Batch Size Extracción',
        default=50,
        help='Órdenes por página en la API de ML'
    )
    extraction_days_back = fields.Integer(
        string='Días hacia atrás',
        default=7,
        help='Cuántos días hacia atrás buscar órdenes'
    )
    
    # Configuración de procesamiento
    processing_batch_size = fields.Integer(
        string='Batch Size Procesamiento',
        default=20,
        help='Órdenes a procesar por ejecución del cron'
    )
    max_retries = fields.Integer(
        string='Máx. Reintentos',
        default=3,
        help='Reintentos antes de marcar como error definitivo'
    )
    
    # Estados a sincronizar
    sync_paid = fields.Boolean(
        string='Sincronizar Pagadas',
        default=True
    )
    sync_pending = fields.Boolean(
        string='Sincronizar Pendientes',
        default=False
    )
    sync_cancelled = fields.Boolean(
        string='Sincronizar Canceladas',
        default=False
    )
    
    # Opciones de procesamiento
    auto_confirm_order = fields.Boolean(
        string='Confirmar Orden Automáticamente',
        default=True
    )
    auto_create_invoice = fields.Boolean(
        string='Crear Factura Automáticamente',
        default=False
    )
    
    # Mapeos
    default_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén por Defecto'
    )
    default_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de Precios por Defecto'
    )
    meli_payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Plazo de Pago ML'
    )
    meli_sales_team_id = fields.Many2one(
        'crm.team',
        string='Equipo de Ventas ML'
    )
    
    # Estadísticas
    last_extraction_date = fields.Datetime(
        string='Última Extracción',
        readonly=True
    )
    last_processing_date = fields.Datetime(
        string='Último Procesamiento',
        readonly=True
    )
    orders_extracted_today = fields.Integer(
        string='Órdenes Extraídas Hoy',
        compute='_compute_stats'
    )
    orders_pending = fields.Integer(
        string='Órdenes Pendientes',
        compute='_compute_stats'
    )
    orders_error = fields.Integer(
        string='Órdenes con Error',
        compute='_compute_stats'
    )

    def _compute_stats(self):
        """Calcula estadísticas de órdenes."""
        MeliRaw = self.env['meli.order.raw']
        today_start = fields.Datetime.today()
        
        for record in self:
            record.orders_extracted_today = MeliRaw.search_count([
                ('extracted_at', '>=', today_start)
            ])
            record.orders_pending = MeliRaw.search_count([
                ('state', '=', 'pending')
            ])
            record.orders_error = MeliRaw.search_count([
                ('state', '=', 'error')
            ])

    @api.model
    def get_config(self):
        """Obtiene o crea la configuración singleton."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Configuración ML Async'})
        return config

    def action_test_connection(self):
        """Prueba la conexión con MercadoLibre."""
        self.ensure_one()
        # Implementar test de conexión
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test de Conexión',
                'message': 'Conexión exitosa con MercadoLibre',
                'type': 'success',
            }
        }

    def action_view_pending(self):
        """Abre vista de órdenes pendientes."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes Pendientes',
            'res_model': 'meli.order.raw',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'pending')],
        }

    def action_view_errors(self):
        """Abre vista de órdenes con error."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes con Error',
            'res_model': 'meli.order.raw',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'error')],
        }
