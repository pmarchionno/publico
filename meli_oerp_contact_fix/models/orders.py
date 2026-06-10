from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class MercadolibreOrders(models.Model):
    _inherit = 'mercadolibre.orders'

    def update_partner_billing_info(self, partner_id, meli_buyer_fields, Receiver):
        """
        Intercepta el diccionario usado para actualizar el partner de facturación,
        asegurando que no se pierdan campos críticos (como parent_id y type) y forzando
        a que se mantenga como individuo.
        """
        # Llamamos al super para que realice el mapeo inicial
        partner_update = super(MercadolibreOrders, self).update_partner_billing_info(partner_id, meli_buyer_fields, Receiver)

        # 1. Forzamos a que el contacto se mantenga como individuo ('person').
        # Esto previene que Odoo rompa el vínculo de parent_id debido a restricciones (compañía hija de persona).
        partner_update['company_type'] = 'person'
        partner_update['is_company'] = False

        # 2. Rescatamos campos críticos que el método original de meli_oerp omite.
        if 'parent_id' in meli_buyer_fields:
            partner_update['parent_id'] = meli_buyer_fields['parent_id']
            
        if 'type' in meli_buyer_fields:
            partner_update['type'] = meli_buyer_fields['type']

        # 3. Nos aseguramos de que el nombre comercial (Razón Social) y CUIT se preserven
        # si se trata del contacto de facturación (type == 'invoice')
        is_invoice = partner_update.get('type') == 'invoice' or (partner_id and partner_id.type == 'invoice')
        if is_invoice:
            if meli_buyer_fields.get('billing_info_business_name'):
                partner_update['name'] = meli_buyer_fields['billing_info_business_name']
            if meli_buyer_fields.get('vat'):
                partner_update['vat'] = meli_buyer_fields['vat']

        return partner_update

    def orders_update_order_json(self, data, context=None, config=None, meli=None):
        """
        Después de que el flujo original de sincronización de ML termina, aseguramos que
        el contacto de facturación recién creado (o actualizado) tenga la Razón Social y el VAT
        correctos, ya que el método original a menudo los omite durante la creación.
        """
        res = super(MercadolibreOrders, self).orders_update_order_json(data, context, config, meli)
        
        try:
            order_json = data.get("order_json", {})
            order_id_str = str(order_json.get("id"))
            
            if not order_id_str or order_id_str == 'None':
                return res

            Partner = self.env['res.partner']
            
            # Buscar el contacto de factura generado (meli_oerp usa el ID de la orden + '-invoice')
            partner_invoice_meli_order_id = "%s-invoice" % order_id_str
            invoice_partner = Partner.search([('meli_order_id', '=', partner_invoice_meli_order_id)], limit=1)
            
            if not invoice_partner:
                return res

            # Extraer info del JSON de la orden
            buyer = order_json.get('buyer', {})
            billing_info = buyer.get('billing_info', {})
            business_name = billing_info.get('BUSINESS_NAME') or buyer.get('business_name')
            cuit = billing_info.get('DOC_NUMBER') or billing_info.get('doc_number')
            
            # Buscar el contacto principal
            buyer_id_str = str(buyer.get('id'))
            main_partner = Partner.search([('meli_buyer_id', '=', buyer_id_str)], limit=1)

            invoice_vals = {}
            
            # 1. Confirmar que tenga el parent_id (si por alguna razón se soltó durante un fallback)
            if main_partner and not invoice_partner.parent_id:
                invoice_vals['parent_id'] = main_partner.id
                
            # 2. Confirmar que tenga la Razón Social de facturación como nombre
            if business_name and invoice_partner.name != business_name:
                invoice_vals['name'] = business_name
                
            # 3. Confirmar que tenga el CUIT
            if cuit and invoice_partner.vat != cuit:
                invoice_vals['vat'] = cuit
                
            # Aplicar parche si hay diferencias
            if invoice_vals:
                invoice_partner.write(invoice_vals)

        except Exception as e:
            _logger.error("Meli OERP Contact Fix - Error corrigiendo contacto en orders_update_order_json: %s", str(e), exc_info=True)
            
        return res
