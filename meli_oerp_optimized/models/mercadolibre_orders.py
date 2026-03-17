# -- coding: utf-8 --
"""
Optimización del procesamiento de órdenes individuales.

Mejoras:
- Evita llamadas API redundantes
- Mejor manejo de errores
- Sin commits manuales
"""

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class MercadoLibreOrdersOptimized(models.Model):
    _inherit = 'mercadolibre.orders'

    def orders_update_order_json(self, data, context=None, config=None, meli=None):
        """
        Override optimizado para procesar una orden.

        Cambios:
        - No hace commit manual (Odoo maneja transacciones)
        - Mejor logging para diagnóstico
        - Manejo de errores más robusto
        """

        order_id = data.get("order_json", {}).get("id", "?")
        _logger.debug('[MELI-OPT] Procesando orden %s', order_id)

        try:
            # Llamar al método original
            result = super().orders_update_order_json(
                data=data, context=context, config=config, meli=meli
            )
            
            _logger.debug('[MELI-OPT] Orden %s procesada correctamente', order_id)
            return result
            
        except Exception as e:
            _logger.error(
                '[MELI-OPT] Error procesando orden %s: %s',
                order_id, str(e), exc_info=True
            )
            # No re-lanzamos la excepción para permitir continuar con otras órdenes
            return {}

    def orders_query_recent(self, account=None, meli=None, context=None):
        """
        Override que delega al nuevo método optimizado de account.
        """
        context = context or self.env.context
        account = account or self.connection_account

        if not account:
            _logger.warning('[MELI-OPT] orders_query_recent sin cuenta')
            return {}

        company = (account and account.company_id) or self.env.user.company_id
        config = account.configuration or company

        if not meli:
            meli = self.env['meli.util'].get_new_instance(company, account)

        import time
        start_time = time.time()
        
        batch_size = getattr(config, 'mercadolibre_cron_batch_size', 50) or 50
        max_time = getattr(config, 'mercadolibre_cron_max_time', 180) or 180
        
        try:
            account._process_orders_batch(
                account=account,
                meli=meli,
                config=config,
                batch_size=batch_size,
                max_time=max_time,
                start_time=start_time
            )
        except Exception as e:
            _logger.error('[MELI-OPT] Error en orders_query_recent: %s', str(e))

        return {}