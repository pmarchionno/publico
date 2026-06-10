from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Interceptamos la creación de contactos provenientes de MercadoLibre (meli_oerp)
            # El contacto principal suele tener 'meli_buyer_id'
            # El contacto de factura suele tener 'meli_order_id' terminado en '-invoice'
            is_meli_main = vals.get('meli_buyer_id')
            meli_order_id = vals.get('meli_order_id')
            is_meli_invoice = isinstance(meli_order_id, str) and '-invoice' in meli_order_id
            
            # Si es un contacto de MercadoLibre, forzamos que sea 'person'
            # para evitar que Odoo rompa la jerarquía (una compañía no puede ser hija de otra persona).
            if is_meli_main or is_meli_invoice:
                vals['company_type'] = 'person'
                vals['is_company'] = False
                
        return super(ResPartner, self).create(vals_list)
