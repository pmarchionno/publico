# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MeliOrderRaw(models.Model):
    """
    Tabla staging para almacenar órdenes crudas de MercadoLibre.
    Permite separar extracción de procesamiento (arquitectura ETL).
    """
    _name = 'meli.order.raw'
    _description = 'MercadoLibre Order Raw Data'
    _order = 'create_date desc'
    _rec_name = 'order_id_ml'

    # Identificación
    order_id_ml = fields.Char(
        string='ID MercadoLibre',
        required=True,
        index=True,
        help='ID único de la orden en MercadoLibre'
    )
    
    # Datos crudos
    json_data = fields.Text(
        string='JSON Data',
        required=True,
        help='JSON crudo de la orden tal como viene de la API de ML'
    )
    
    # Estado de procesamiento
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('done', 'Procesado'),
        ('error', 'Error'),
        ('skipped', 'Omitido'),
    ], string='Estado', default='pending', index=True, required=True)
    
    # Trazabilidad
    error_message = fields.Text(
        string='Mensaje de Error',
        help='Detalle del error si el procesamiento falló'
    )
    retry_count = fields.Integer(
        string='Intentos',
        default=0,
        help='Cantidad de veces que se intentó procesar'
    )
    max_retries = fields.Integer(
        string='Máx. Reintentos',
        default=3
    )
    
    # Fechas
    extracted_at = fields.Datetime(
        string='Fecha Extracción',
        default=fields.Datetime.now,
        help='Momento en que se descargó de ML'
    )
    processed_at = fields.Datetime(
        string='Fecha Procesamiento',
        help='Momento en que se procesó exitosamente'
    )
    
    # Relación con orden procesada
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de Venta',
        help='Orden de venta creada a partir de este registro'
    )
    
    # Campos extraídos del JSON para filtros rápidos
    ml_status = fields.Char(
        string='Estado ML',
        compute='_compute_json_fields',
        store=True,
        help='Estado de la orden en MercadoLibre'
    )
    ml_date_created = fields.Datetime(
        string='Fecha Creación ML',
        compute='_compute_json_fields',
        store=True
    )
    ml_total_amount = fields.Float(
        string='Monto Total',
        compute='_compute_json_fields',
        store=True
    )
    ml_buyer_nickname = fields.Char(
        string='Comprador',
        compute='_compute_json_fields',
        store=True
    )

    _sql_constraints = [
        ('order_id_ml_uniq', 'unique(order_id_ml)', 
         'Ya existe un registro con este ID de MercadoLibre!')
    ]

    @api.depends('json_data')
    def _compute_json_fields(self):
        """Extrae campos del JSON para facilitar filtros y búsquedas."""
        for record in self:
            if record.json_data:
                try:
                    data = json.loads(record.json_data)
                    record.ml_status = data.get('status', '')
                    record.ml_total_amount = data.get('total_amount', 0.0)
                    
                    # Fecha de creación
                    date_created = data.get('date_created')
                    if date_created:
                        # Formato: 2024-01-15T10:30:00.000-03:00
                        record.ml_date_created = datetime.fromisoformat(
                            date_created.replace('Z', '+00:00')
                        )
                    else:
                        record.ml_date_created = False
                    
                    # Comprador
                    buyer = data.get('buyer', {})
                    record.ml_buyer_nickname = buyer.get('nickname', '')
                    
                except (json.JSONDecodeError, ValueError) as e:
                    _logger.warning(f"Error parseando JSON de orden {record.order_id_ml}: {e}")
                    record.ml_status = ''
                    record.ml_date_created = False
                    record.ml_total_amount = 0.0
                    record.ml_buyer_nickname = ''
            else:
                record.ml_status = ''
                record.ml_date_created = False
                record.ml_total_amount = 0.0
                record.ml_buyer_nickname = ''

    def get_json_data(self):
        """Retorna el JSON parseado."""
        self.ensure_one()
        if self.json_data:
            return json.loads(self.json_data)
        return {}

    def action_reprocess(self):
        """Acción manual para reprocesar órdenes con error."""
        for record in self:
            if record.state in ('error', 'skipped'):
                record.write({
                    'state': 'pending',
                    'error_message': False,
                    'retry_count': 0,
                })
        return True

    def action_view_json(self):
        """Abre wizard para ver JSON formateado."""
        self.ensure_one()
        try:
            formatted = json.dumps(json.loads(self.json_data), indent=2, ensure_ascii=False)
        except:
            formatted = self.json_data
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'JSON Orden {self.order_id_ml}',
            'res_model': 'meli.order.raw.json.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_json_formatted': formatted,
                'default_order_raw_id': self.id,
            }
        }

    @api.model
    def cleanup_old_records(self, days=30):
        """
        Limpia registros procesados antiguos.
        Llamar desde cron de mantenimiento.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        old_records = self.search([
            ('state', '=', 'done'),
            ('processed_at', '<', cutoff_date),
        ])
        count = len(old_records)
        old_records.unlink()
        _logger.info(f"Limpieza: eliminados {count} registros procesados con más de {days} días")
        return count


class MeliOrderRawJsonWizard(models.TransientModel):
    """Wizard para visualizar JSON formateado."""
    _name = 'meli.order.raw.json.wizard'
    _description = 'Ver JSON de Orden ML'

    order_raw_id = fields.Many2one('meli.order.raw', string='Orden Raw')
    json_formatted = fields.Text(string='JSON', readonly=True)
