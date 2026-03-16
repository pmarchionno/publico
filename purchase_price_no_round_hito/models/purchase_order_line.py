# -*- coding: utf-8 -*-
##############################################################################
# Purchase Price No Round (Hito)
# Ticket: TK#2026/03157
#
# Módulo propio de Hitofusion
# Basado en: purchase_price_no_round (pmarchionno)
#
# Problema: Odoo redondea el precio de supplierinfo a 2 decimales
# Solución: Override del compute sin float_round()
# Mejora: Integración nativa con product_replenishment_cost (net_price)
##############################################################################
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends('product_qty', 'product_uom', 'company_id', 'order_id.partner_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        """
        Override para evitar el redondeo prematuro del precio.
        
        Cambios respecto al core:
        1. NO usa float_round() para el precio
        2. Mantiene la precisión completa del supplierinfo
        3. Usa net_price de product_replenishment_cost cuando está disponible
        """
        for line in self:
            if not line.product_id:
                continue
                
            # Obtener parámetros para buscar seller
            params = line._get_select_sellers_params()
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=line.product_uom,
                params=params,
            )

            # Actualizar date_planned
            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # Si no hay seller, usar standard_price
            if not seller:
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id
                )
                if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
                    # Mantener el precio existente sin cambios
                    continue
                    
                # Usar standard_price con conversión de moneda
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.standard_price,
                    line.product_id.supplier_taxes_id,
                    line.taxes_id,
                    line.company_id
                )
                price_unit = line.product_id.cost_currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order or fields.Date.context_today(line),
                    round=False,  # NO redondear en conversión
                )
                # Asignar SIN redondear
                line.price_unit = price_unit
                
            else:
                # Hay seller - usar net_price (de product_replenishment_cost) o price
                # net_price incluye las reglas de costo de reposición
                seller_price = seller.net_price if seller.net_price else seller.price
                
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    seller_price,
                    line.product_id.supplier_taxes_id,
                    line.taxes_id,
                    line.company_id
                )
                
                # Conversión de moneda SIN redondeo
                price_unit = seller.currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order or fields.Date.context_today(line),
                    round=False,  # NO redondear en conversión
                )
                
                # Conversión de UoM si es necesario
                if seller.product_uom and seller.product_uom != line.product_uom:
                    price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)
                
                # Asignar precio SIN float_round()
                line.price_unit = price_unit
                
                # Asignar descuento si existe
                line.discount = seller.discount or 0.0

            # Actualizar nombre/descripción del producto
            vendors = line.product_id._prepare_sellers(params=params)
            product_ctx = {
                'seller_id': seller.id if seller else (vendors[0].id if vendors else None),
                'partner_id': line.partner_id.id if line.partner_id else None,
                'lang': line.partner_id.lang if line.partner_id else line.env.lang,
            }
            line.name = line._get_product_purchase_description(line.product_id.with_context(**product_ctx))
