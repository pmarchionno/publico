# -- coding: utf-8 --
"""
Optimización del cron de órdenes de MercadoLibre.

Problemas identificados en el código original:
1. Procesamiento secuencial sin límite de registros
2. Commits manuales dentro de loops (anti-patrón Odoo)
3. Sin control de tiempo de ejecución
4. Recursión para paginación (puede causar stack overflow)
5. Todas las cuentas en una sola ejecución

Soluciones implementadas:
1. Procesamiento por lotes con límite configurable
2. Control de tiempo máximo de ejecución
3. Paginación con estado persistente
4. Sin commits manuales (Odoo maneja transacciones)
5. Procesamiento incremental entre ejecuciones
"""

import time
import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class MercadoLibreAccountOptimized(models.Model):
    _inherit = 'mercadolibre.account'
    def cron_meli_orders(self):
        """
        Override del cron de órdenes con optimizaciones para Odoo.sh.

        Cambios principales:
        - Procesa un lote limitado de órdenes por ejecución
        - Controla tiempo de ejecución para evitar timeout
        - Guarda estado de paginación entre ejecuciones
        - No hace commits manuales
        """
        start_time = time.time()

        for connacc in self:
            company = connacc.company_id or self.env.user.company_id
            config = connacc.configuration or company

            # Obtener parámetros de optimización
            batch_size = getattr(config, 'mercadolibre_cron_batch_size', 50) or 50
            max_time = getattr(config, 'mercadolibre_cron_max_time', 180) or 180

            _logger.info(
                '[MELI-OPT] Iniciando cron_meli_orders para %s (batch=%d, max_time=%ds)',
                connacc.name, batch_size, max_time
            )

            # Verificar conexión API
            apistate = self.env['meli.util'].get_new_instance(company, connacc)
            if apistate.needlogin_state:
                _logger.warning('[MELI-OPT] %s requiere login, saltando...', connacc.name)
                continue

            # Solo procesar si el cron de órdenes está habilitado
            if not getattr(config, 'mercadolibre_cron_get_orders', False):
                _logger.info('[MELI-OPT] Cron de órdenes deshabilitado para %s', connacc.name)
                continue

            # Procesar órdenes con límites
            try:
                self._process_orders_batch(
                    account=connacc,
                    meli=apistate,
                    config=config,
                    batch_size=batch_size,
                    max_time=max_time,
                    start_time=start_time
                )
            except Exception as e:
                _logger.error(
                    '[MELI-OPT] Error procesando órdenes de %s: %s',
                    connacc.name, str(e), exc_info=True
                )

            # Verificar tiempo total
            elapsed = time.time() - start_time
            if elapsed > max_time:
                _logger.warning(
                    '[MELI-OPT] Tiempo máximo alcanzado (%.1fs), deteniendo cron',
                    elapsed
                )
                break

        elapsed_total = time.time() - start_time
        _logger.info('[MELI-OPT] Cron finalizado en %.1f segundos', elapsed_total)

    def _process_orders_batch(self, account, meli, config, batch_size, max_time, start_time):
        """
        Procesa un lote de órdenes con control de límites.

        Args:
            account: mercadolibre.account
            meli: instancia de API
            config: configuración
            batch_size: máximo de órdenes a procesar
            max_time: tiempo máximo en segundos
            start_time: timestamp de inicio
        """
        orders_obj = self.env['mercadolibre.orders']

        # Obtener offset guardado (paginación incremental)
        last_offset = getattr(config, 'mercadolibre_cron_last_offset', 0) or 0
        orders_per_page = getattr(config, 'mercadolibre_cron_orders_per_page', 50) or 50
        orders_per_page = min(orders_per_page, 50)   # ML permite máximo 50

        processed_count = 0
        current_offset = last_offset
        has_more = True

        _logger.info(
            '[MELI-OPT] Procesando desde offset %d, batch_size=%d',
            current_offset, batch_size
        )

        while has_more and processed_count < batch_size:
            # Verificar tiempo
            elapsed = time.time() - start_time
            if elapsed > max_time * 0.9: # 90% del tiempo máximo
                _logger.warning(
                    '[MELI-OPT] Acercándose al tiempo máximo, guardando estado')
                break

            # Consultar página de órdenes
            orders_query = (
                f"/orders/search?seller={meli.seller_id}"
                f"&sort=date_desc&limit={orders_per_page}&offset={current_offset}"
            )
            
            try:
                response = meli.get(orders_query, {'access_token': meli.access_token})
                orders_json = response.json()
            except Exception as e:
                _logger.error('[MELI-OPT] Error en API: %s', str(e))
                break

            if "error" in orders_json:
                _logger.error('[MELI-OPT] Error API ML: %s', orders_json.get("message", ""))
                break

            # Procesar resultados
            results = orders_json.get("results", [])
            paging = orders_json.get("paging", {})
            total = paging.get("total", 0)
            
            if not results:
                _logger.info('[MELI-OPT] No hay más órdenes para procesar')
                # Resetear offset para próxima ejecución
                self._save_cron_offset(config, 0)
                break

            _logger.info(
                '[MELI-OPT] Procesando %d órdenes (offset=%d, total=%d)',
                len(results), current_offset, total
            )

            # Procesar cada orden del lote
            for order_json in results:
                if processed_count >= batch_size:
                    break
                    
                if not order_json:
                    continue

                try:
                    pdata = {"id": False, "order_json": order_json}
                    orders_obj.orders_update_order_json(
                        data=pdata, config=config, meli=meli
                    )
                    processed_count += 1
                except Exception as e:
                    _logger.error(
                        '[MELI-OPT] Error procesando orden %s: %s',
                        order_json.get("id", "?"), str(e)
                    )

            # Calcular siguiente offset
            current_offset += len(results)
            
            # Verificar si hay más páginas
            has_more = current_offset < total and processed_count < batch_size

        # Guardar offset para próxima ejecución
        if has_more:
            self._save_cron_offset(config, current_offset)
            _logger.info('[MELI-OPT] Guardando offset %d para próxima ejecución', current_offset)
        else:
            self._save_cron_offset(config, 0)
            _logger.info('[MELI-OPT] Paginación completada, reseteando offset')

        _logger.info('[MELI-OPT] Procesadas %d órdenes en esta ejecución', processed_count)

    def _save_cron_offset(self, config, offset):
        """Guarda el offset de paginación de forma segura."""
        try:
            if hasattr(config, 'mercadolibre_cron_last_offset'):
                config.sudo().write({'mercadolibre_cron_last_offset': offset})
        except Exception as e:
            _logger.warning('[MELI-OPT] No se pudo guardar offset: %s', str(e))