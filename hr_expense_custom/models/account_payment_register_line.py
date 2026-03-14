# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPaymentRegisterLine(models.TransientModel):
    """
    Líneas de pago para el wizard de registro de pago.
    Usado cuando se selecciona el método 'payment_bundle' (Pagos Múltiples).
    Cada línea representa un pago individual con su propio diario y monto.
    """
    _name = 'account.payment.register.line'
    _description = 'Payment Register Line'

    wizard_id = fields.Many2one(
        'account.payment.register',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    
    company_id = fields.Many2one(
        related='wizard_id.company_id',
        store=True,
    )
    
    currency_id = fields.Many2one(
        related='wizard_id.currency_id',
    )
    
    company_currency_id = fields.Many2one(
        related='wizard_id.company_currency_id',
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Método de Pago',
        domain="[('journal_id', '=', journal_id), ('payment_method_id.payment_type', '=', parent.payment_type)]",
    )
    
    amount = fields.Monetary(
        string='Monto',
        currency_field='company_currency_id',
        required=True,
    )
    
    receiptbook_id = fields.Many2one(
        'account.payment.receiptbook',
        string='Talonario',
        domain="[('journal_id', '=', journal_id), ('payment_type', '=', parent.payment_type)]",
    )
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Auto-seleccionar método de pago y talonario por defecto del diario"""
        if self.journal_id:
            # Método de pago por defecto
            payment_type = self.wizard_id.payment_type or 'outbound'
            if payment_type == 'outbound':
                methods = self.journal_id.outbound_payment_method_line_ids
            else:
                methods = self.journal_id.inbound_payment_method_line_ids
            
            # Excluir payment_bundle de los métodos disponibles para líneas
            methods = methods.filtered(lambda m: m.payment_method_id.code != 'payment_bundle')
            if methods:
                self.payment_method_line_id = methods[0]
            
            # Talonario por defecto
            receiptbook = self.env['account.payment.receiptbook'].search([
                ('journal_id', '=', self.journal_id.id),
                ('payment_type', '=', payment_type),
            ], limit=1)
            if receiptbook:
                self.receiptbook_id = receiptbook
