# -*- coding: utf-8 -*-
##############################################################################
#
#    Módulo para unificar contactos duplicados de MercadoLibre
#    Copyright (C) 2026 HITOFUSION
#
##############################################################################

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir create para interceptar órdenes de MercadoLibre
        y unificar contactos antes de crear la orden.
        """
        for vals in vals_list:
            # Si es una orden de MercadoLibre
            if vals.get('meli_order_id') or vals.get('client_order_ref', '').startswith('ML'):
                # Verificar si hay contactos para unificar
                self._unificar_contactos_meli(vals)
        
        return super(SaleOrder, self).create(vals_list)

    def write(self, vals):
        """
        Sobrescribir write para interceptar cambios en órdenes de MercadoLibre
        """
        if 'partner_id' in vals or 'partner_invoice_id' in vals:
            for order in self:
                if order.meli_order_id or (order.client_order_ref and order.client_order_ref.startswith('ML')):
                    # Verificar si hay contactos para unificar
                    self._unificar_contactos_meli(vals)
        
        return super(SaleOrder, self).write(vals)

    @api.model
    def _unificar_contactos_meli(self, vals):
        """
        Verifica si los contactos de la orden pueden ser unificados
        y realiza la unificación antes de crear/actualizar la orden.
        """
        partner_obj = self.env['res.partner']
        
        # Verificar contacto de facturación
        if vals.get('partner_invoice_id'):
            invoice = partner_obj.browse(vals['partner_invoice_id'])
            if invoice.exists() and invoice.type == 'invoice':
                # Buscar si hay un contacto principal similar
                principal = partner_obj._buscar_contacto_principal_para_unificar(invoice)
                
                if principal:
                    # Unificar el contacto de facturación con el principal
                    partner_obj._unificar_contacto(principal, invoice)
                    
                    # Actualizar vals para que apunte al principal
                    vals['partner_invoice_id'] = principal.id
                    
                    # Si el partner_id era el invoice, actualizarlo también
                    if vals.get('partner_id') == invoice.id:
                        vals['partner_id'] = principal.id
                    
                    _logger.info(
                        "Orden ML: contacto de facturación unificado. "
                        "Nuevo partner_invoice_id: %s (id:%s)",
                        principal.name, principal.id
                    )
        
        return vals