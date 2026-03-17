# -*- coding: utf-8 -*-
import json
import logging
import requests
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__name__)

MELI_API_BASE = 'https://api.mercadolibre.com'


class MeliSyncService(models.AbstractModel):
    """
    Servicio de sincronización ETL para MercadoLibre.
    
    Arquitectura:
    - FASE 1 (Extracción): Descarga órdenes y guarda JSON crudo
    - FASE 2 (Procesamiento): Procesa JSON y crea/actualiza registros Odoo
    """
    _name = 'meli.sync.service'
    _description = 'Servicio de Sincronización MercadoLibre'

    # =========================================================================
    # FASE 1: EXTRACCIÓN
    # =========================================================================
    
    @api.model
    def cron_extract_orders(self):
        """
        CRON: Extrae órdenes de MercadoLibre y guarda en staging.
        Diseñado para ser rápido - solo I/O de red, sin procesamiento.
        """
        config = self.env['meli.async.config'].get_config()
        
        if not config.access_token or not config.seller_id:
            _logger.warning("MeLi Sync: Faltan credenciales, saltando extracción")
            return False
        
        _logger.info("MeLi Sync: Iniciando extracción de órdenes")
        
        try:
            orders_extracted = self._extract_orders_from_ml(config)
            config.write({'last_extraction_date': fields.Datetime.now()})
            _logger.info(f"MeLi Sync: Extracción completada - {orders_extracted} órdenes")
            return orders_extracted
            
        except Exception as e:
            _logger.error(f"MeLi Sync: Error en extracción - {str(e)}")
            raise

    def _extract_orders_from_ml(self, config):
        """
        Llama a la API de ML y guarda las órdenes en meli.order.raw.
        """
        MeliRaw = self.env['meli.order.raw']
        orders_extracted = 0
        offset = 0
        batch_size = config.extraction_batch_size or 50
        
        # Calcular fecha desde
        date_from = datetime.now() - timedelta(days=config.extraction_days_back or 7)
        date_from_str = date_from.strftime('%Y-%m-%dT00:00:00.000-00:00')
        
        # Construir filtro de estados
        statuses = []
        if config.sync_paid:
            statuses.append('paid')
        if config.sync_pending:
            statuses.append('pending')
        if not statuses:
            statuses = ['paid']  # Default
        
        headers = {
            'Authorization': f'Bearer {config.access_token}',
            'Content-Type': 'application/json',
        }
        
        while True:
            # Llamar API de órdenes
            url = f"{MELI_API_BASE}/orders/search"
            params = {
                'seller': config.seller_id,
                'order.status': ','.join(statuses),
                'order.date_created.from': date_from_str,
                'offset': offset,
                'limit': batch_size,
                'sort': 'date_desc',
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 401:
                # Token expirado - intentar refresh
                self._refresh_token(config)
                headers['Authorization'] = f'Bearer {config.access_token}'
                response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                _logger.error(f"MeLi API Error: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                break
            
            # Guardar cada orden en staging
            for order_data in results:
                order_id_ml = str(order_data.get('id'))
                
                # Verificar si ya existe
                existing = MeliRaw.search([('order_id_ml', '=', order_id_ml)], limit=1)
                
                if existing:
                    # Actualizar JSON si cambió el estado
                    if existing.state in ('pending', 'error'):
                        existing.write({
                            'json_data': json.dumps(order_data),
                            'extracted_at': fields.Datetime.now(),
                        })
                else:
                    # Crear nuevo registro
                    MeliRaw.create({
                        'order_id_ml': order_id_ml,
                        'json_data': json.dumps(order_data),
                        'state': 'pending',
                        'max_retries': config.max_retries or 3,
                    })
                    orders_extracted += 1
            
            # Siguiente página
            total = data.get('paging', {}).get('total', 0)
            offset += batch_size
            
            if offset >= total:
                break
        
        return orders_extracted

    def _refresh_token(self, config):
        """Renueva el access_token usando el refresh_token."""
        if not config.refresh_token:
            raise UserError("No hay refresh_token configurado")
        
        url = f"{MELI_API_BASE}/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'refresh_token': config.refresh_token,
        }
        
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            tokens = response.json()
            config.write({
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
            })
            _logger.info("MeLi Sync: Token renovado exitosamente")
        else:
            _logger.error(f"MeLi Sync: Error renovando token - {response.text}")
            raise UserError("Error renovando token de MercadoLibre")

    # =========================================================================
    # FASE 2: PROCESAMIENTO
    # =========================================================================

    @api.model
    def cron_process_orders(self):
        """
        CRON: Procesa órdenes pendientes de la tabla staging.
        Usa queue_job para procesamiento asíncrono.
        """
        config = self.env['meli.async.config'].get_config()
        batch_size = config.processing_batch_size or 20
        
        # Buscar órdenes pendientes
        pending_orders = self.env['meli.order.raw'].search([
            ('state', '=', 'pending'),
        ], limit=batch_size, order='extracted_at asc')
        
        _logger.info(f"MeLi Sync: Procesando {len(pending_orders)} órdenes")
        
        for order_raw in pending_orders:
            # Encolar job para cada orden
            self.with_delay(
                priority=10,
                max_retries=config.max_retries or 3,
                description=f"Procesar orden ML {order_raw.order_id_ml}"
            )._process_single_order(order_raw.id)
        
        config.write({'last_processing_date': fields.Datetime.now()})
        return len(pending_orders)

    @job(default_channel='root.meli')
    def _process_single_order(self, order_raw_id):
        """
        JOB: Procesa una orden individual.
        Ejecutado asíncronamente por queue_job.
        """
        order_raw = self.env['meli.order.raw'].browse(order_raw_id)
        
        if not order_raw.exists():
            _logger.warning(f"MeLi Sync: Orden raw {order_raw_id} no existe")
            return False
        
        if order_raw.state != 'pending':
            _logger.info(f"MeLi Sync: Orden {order_raw.order_id_ml} ya no está pendiente")
            return False
        
        # Marcar como procesando
        order_raw.write({'state': 'processing'})
        
        try:
            order_data = order_raw.get_json_data()
            
            # Crear o actualizar orden de venta
            sale_order = self._create_or_update_sale_order(order_data)
            
            # Marcar como procesado
            order_raw.write({
                'state': 'done',
                'processed_at': fields.Datetime.now(),
                'sale_order_id': sale_order.id,
                'error_message': False,
            })
            
            _logger.info(f"MeLi Sync: Orden {order_raw.order_id_ml} procesada -> SO {sale_order.name}")
            return sale_order.id
            
        except Exception as e:
            error_msg = str(e)
            order_raw.retry_count += 1
            
            if order_raw.retry_count >= order_raw.max_retries:
                order_raw.write({
                    'state': 'error',
                    'error_message': f"Error después de {order_raw.retry_count} intentos: {error_msg}",
                })
                _logger.error(f"MeLi Sync: Orden {order_raw.order_id_ml} falló definitivamente: {error_msg}")
            else:
                order_raw.write({
                    'state': 'pending',  # Volver a pendiente para reintentar
                    'error_message': f"Intento {order_raw.retry_count}: {error_msg}",
                })
                _logger.warning(f"MeLi Sync: Orden {order_raw.order_id_ml} reintentará: {error_msg}")
            
            raise  # Re-raise para que queue_job maneje el reintento

    def _create_or_update_sale_order(self, order_data):
        """
        Crea o actualiza una orden de venta a partir del JSON de ML.
        """
        config = self.env['meli.async.config'].get_config()
        SaleOrder = self.env['sale.order']
        
        order_id_ml = str(order_data.get('id'))
        
        # Buscar si ya existe
        existing_order = SaleOrder.search([
            ('client_order_ref', '=', order_id_ml)
        ], limit=1)
        
        if existing_order:
            # Actualizar estado si es necesario
            self._update_existing_order(existing_order, order_data)
            return existing_order
        
        # Crear nueva orden
        partner = self._get_or_create_partner(order_data.get('buyer', {}))
        
        order_lines = []
        for item in order_data.get('order_items', []):
            line_vals = self._prepare_order_line(item)
            if line_vals:
                order_lines.append((0, 0, line_vals))
        
        # Datos de envío
        shipping = order_data.get('shipping', {})
        
        order_vals = {
            'partner_id': partner.id,
            'client_order_ref': order_id_ml,
            'order_line': order_lines,
            'date_order': self._parse_ml_date(order_data.get('date_created')),
            'note': f"Orden MercadoLibre: {order_id_ml}\nEstado ML: {order_data.get('status')}",
        }
        
        # Aplicar configuraciones
        if config.default_warehouse_id:
            order_vals['warehouse_id'] = config.default_warehouse_id.id
        if config.default_pricelist_id:
            order_vals['pricelist_id'] = config.default_pricelist_id.id
        if config.meli_payment_term_id:
            order_vals['payment_term_id'] = config.meli_payment_term_id.id
        if config.meli_sales_team_id:
            order_vals['team_id'] = config.meli_sales_team_id.id
        
        sale_order = SaleOrder.create(order_vals)
        
        # Auto confirmar si está configurado
        if config.auto_confirm_order and order_data.get('status') == 'paid':
            sale_order.action_confirm()
        
        return sale_order

    def _get_or_create_partner(self, buyer_data):
        """Obtiene o crea el partner del comprador."""
        Partner = self.env['res.partner']
        
        ml_buyer_id = str(buyer_data.get('id', ''))
        nickname = buyer_data.get('nickname', 'Cliente ML')
        email = buyer_data.get('email', '')
        
        # Buscar por ID de ML
        partner = Partner.search([
            ('comment', 'ilike', f'ML_ID:{ml_buyer_id}')
        ], limit=1)
        
        if partner:
            return partner
        
        # Buscar por email
        if email:
            partner = Partner.search([('email', '=', email)], limit=1)
            if partner:
                return partner
        
        # Crear nuevo
        return Partner.create({
            'name': nickname,
            'email': email,
            'comment': f'ML_ID:{ml_buyer_id}',
            'customer_rank': 1,
        })

    def _prepare_order_line(self, item_data):
        """Prepara los valores para una línea de orden."""
        Product = self.env['product.product']
        
        ml_item_id = item_data.get('item', {}).get('id', '')
        sku = item_data.get('item', {}).get('seller_sku', '')
        title = item_data.get('item', {}).get('title', 'Producto ML')
        quantity = item_data.get('quantity', 1)
        unit_price = item_data.get('unit_price', 0)
        
        # Buscar producto por SKU o referencia ML
        product = None
        if sku:
            product = Product.search([('default_code', '=', sku)], limit=1)
        
        if not product:
            product = Product.search([
                ('default_code', '=', ml_item_id)
            ], limit=1)
        
        if not product:
            # Crear producto genérico o usar uno por defecto
            product = Product.search([('default_code', '=', 'MELI-DEFAULT')], limit=1)
            if not product:
                product = Product.create({
                    'name': title,
                    'default_code': ml_item_id,
                    'type': 'consu',
                    'list_price': unit_price,
                })
        
        return {
            'product_id': product.id,
            'name': title,
            'product_uom_qty': quantity,
            'price_unit': unit_price,
        }

    def _update_existing_order(self, sale_order, order_data):
        """Actualiza una orden existente si el estado cambió."""
        ml_status = order_data.get('status')
        
        # Agregar nota sobre actualización
        sale_order.message_post(
            body=f"Actualización desde ML: Estado = {ml_status}"
        )

    def _parse_ml_date(self, date_str):
        """Parsea fecha de MercadoLibre a datetime."""
        if not date_str:
            return fields.Datetime.now()
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return fields.Datetime.now()

    # =========================================================================
    # ACCIONES MANUALES
    # =========================================================================

    @api.model
    def action_manual_extract(self):
        """Extracción manual desde botón."""
        return self.cron_extract_orders()

    @api.model
    def action_manual_process(self):
        """Procesamiento manual desde botón."""
        return self.cron_process_orders()

    @api.model
    def action_reprocess_errors(self):
        """Reprocesa todas las órdenes con error."""
        error_orders = self.env['meli.order.raw'].search([('state', '=', 'error')])
        error_orders.action_reprocess()
        return len(error_orders)
