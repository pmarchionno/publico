# -- coding: utf-8 --
from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    """
    Hereda el wizard de registro de pago para agregar el campo de 
    Talonario de Recibo cuando se paga desde Gastos.

    Agrega funcionalidad para seleccionar un talonario de recibo al registrar
    pagos desde el módulo de Gastos (hr_expense), replicando la funcionalidad
    disponible en "Pagos de Proveedores" de Contabilidad.
    """
    _inherit = 'account.payment.register'

    receiptbook_id = fields.Many2one(
        'account.payment.receiptbook',
        string='Talonario de Recibo',
    )

    @api.model
    def default_get(self, fields_list):
        """
        Override para autocompletar el talonario por defecto.
        
        Busca automáticamente el primer talonario disponible si el user no 
        selecciona uno manualmente. Intenta filtrar por diario si ese
        campo existe en el comodel real de receiptbook_id.
        """
        res = super().default_get(fields_list)

        # Autocompletar talonario si no está definido y se requiere
        if 'receiptbook_id' in fields_list and not res.get('receiptbook_id'):
            try:
                receiptbook_field = self._fields.get('receiptbook_id')
                if not receiptbook_field or receiptbook_field.type != 'many2one':
                    return res

                model_name = receiptbook_field.comodel_name
                if not model_name or model_name not in self.env.registry:
                    return res

                receiptbook_model = self.env[model_name]
                domain = []
                
                # Filtrar por diario si existe ese campo y se tiene journal_id
                journal_id = res.get('journal_id')
                if journal_id and 'journal_id' in receiptbook_model._fields:
                    domain.append(('journal_id', '=', journal_id))
                
                # Buscar el primer talonario disponible con los filtros aplicables
                receiptbook = receiptbook_model.search(domain, limit=1)
                if receiptbook:
                    # Asignar talonario por defecto
                    res['receiptbook_id'] = receiptbook.id
            except Exception:
                # Si algo falla, continuar sin asignar talonario por defecto
                pass

        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Override para propagar el receiptbook_id al pago creado.
        
        Si receiptbook_id está seleccionado y existe en account.payment,
        lo propaga al pago.
        """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        
        try:
            if 'receiptbook_id' in self._fields and self.receiptbook_id:
                payment_model_fields = self.env['account.payment']._fields
                if 'receiptbook_id' in payment_model_fields:
                    # Propagar el talonario al pago
                    payment_vals['receiptbook_id'] = self.receiptbook_id.id
        except Exception:
            # Si algo falla, continuar sin propagar
            pass
            
        return payment_vals
        