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
        'res.company',
        related='wizard_id.company_id',
        store=True,
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.company_currency_id',
    )
    
    payment_type = fields.Selection(
        related='wizard_id.payment_type',
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
        compute='_compute_payment_method_line_id',
        store=True,
        readonly=False,
    )
    
    amount = fields.Monetary(
        string='Monto',
        currency_field='company_currency_id',
        required=True,
    )
    
    receiptbook_id = fields.Many2one(
        'account.payment.receiptbook',
        string='Talonario',
        domain="[('journal_id', '=', journal_id), ('partner_type', '=', payment_type)]",
    )
    
    @api.depends('journal_id', 'payment_type')
    def _compute_payment_method_line_id(self):
        """Auto-seleccionar método de pago por defecto del diario"""
        for line in self:
            if not line.journal_id:
                line.payment_method_line_id = False
                continue
                
            payment_type = line.payment_type or 'outbound'
            if payment_type == 'outbound':
                methods = line.journal_id.outbound_payment_method_line_ids
            else:
                methods = line.journal_id.inbound_payment_method_line_ids
            
            # Excluir payment_bundle de los métodos disponibles para líneas hijas
            methods = methods.filtered(lambda m: m.payment_method_id.code != 'payment_bundle')
            line.payment_method_line_id = methods[0] if methods else False
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Auto-seleccionar talonario por defecto del diario"""
        if self.journal_id:
            payment_type = self.payment_type or 'outbound'
            receiptbook = self.env['account.payment.receiptbook'].search([
                ('journal_id', '=', self.journal_id.id),
                ('partner_type', '=', payment_type),
            ], limit=1)
            self.receiptbook_id = receiptbook if receiptbook else False
