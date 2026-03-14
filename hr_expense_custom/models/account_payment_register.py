# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command


class AccountPaymentRegister(models.TransientModel):
    """
    Hereda el wizard de registro de pago para agregar:
    1. Campo de Talonario de Recibo cuando se paga desde Gastos
    2. Soporte para Pagos Múltiples (payment_bundle) con líneas de pago
    """
    _inherit = 'account.payment.register'

    # === Campos para detección de contexto ===
    is_from_expense = fields.Boolean(
        string='Es pago de gasto',
        compute='_compute_is_from_expense',
    )
    
    # === Campos para Payment Bundle ===
    is_payment_bundle = fields.Boolean(
        string='Es Pago Múltiple',
        compute='_compute_is_payment_bundle',
    )
    
    payment_line_ids = fields.One2many(
        'account.payment.register.line',
        'wizard_id',
        string='Líneas de Pago',
    )
    
    payment_lines_total = fields.Monetary(
        string='Total Líneas',
        compute='_compute_payment_lines_total',
        currency_field='company_currency_id',
    )
    
    payment_lines_difference = fields.Monetary(
        string='Diferencia',
        compute='_compute_payment_lines_total',
        currency_field='company_currency_id',
    )

    # === Computes ===
    
    @api.depends('line_ids')
    def _compute_is_from_expense(self):
        """Detecta si el wizard fue abierto desde un reporte de gastos."""
        for wizard in self:
            expense_moves = wizard.line_ids.mapped('move_id').filtered(
                lambda m: m.expense_sheet_id
            )
            wizard.is_from_expense = bool(expense_moves)

    @api.depends('payment_method_line_id')
    def _compute_is_payment_bundle(self):
        """Detecta si el método de pago es 'payment_bundle' (Pagos Múltiples)."""
        for wizard in self:
            wizard.is_payment_bundle = (
                wizard.payment_method_line_id.payment_method_id.code == 'payment_bundle'
            )

    @api.depends('payment_line_ids.amount', 'amount')
    def _compute_payment_lines_total(self):
        """Calcula el total de las líneas de pago y la diferencia con el monto a pagar."""
        for wizard in self:
            total = sum(wizard.payment_line_ids.mapped('amount'))
            wizard.payment_lines_total = total
            wizard.payment_lines_difference = wizard.amount - total

    # === Defaults ===
    
    @api.model
    def default_get(self, fields_list):
        """Override para establecer valores por defecto del talonario."""
        res = super().default_get(fields_list)
        
        # Talonario por defecto cuando viene de expense
        if self.env.context.get('active_model') == 'hr.expense.sheet':
            if 'receiptbook_id' in fields_list and not res.get('receiptbook_id'):
                journal_id = res.get('journal_id')
                if journal_id:
                    journal = self.env['account.journal'].browse(journal_id)
                    receiptbook = self.env['account.payment.receiptbook'].search([
                        ('journal_id', '=', journal.id),
                        ('payment_type', '=', 'outbound'),
                    ], limit=1)
                    if receiptbook:
                        res['receiptbook_id'] = receiptbook.id
        
        return res

    # === Onchange ===
    
    @api.onchange('is_payment_bundle')
    def _onchange_is_payment_bundle(self):
        """Cuando cambia a payment_bundle, limpiar líneas previas."""
        if not self.is_payment_bundle:
            self.payment_line_ids = [Command.clear()]

    # === Override de creación de pago ===
    
    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Override para:
        1. Propagar receiptbook_id al pago
        2. Manejar payment_bundle creando pago principal + link_payment_ids
        """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        
        # Propagar receiptbook_id
        if self.receiptbook_id and 'receiptbook_id' not in payment_vals:
            payment_vals['receiptbook_id'] = self.receiptbook_id.id
        
        # Si es payment_bundle con líneas, preparar la estructura
        if self.is_payment_bundle and self.payment_line_ids:
            # El pago principal tiene amount=0
            payment_vals['amount'] = 0
            
            # Crear los valores de los pagos hijos
            link_payment_vals = []
            for line in self.payment_line_ids:
                child_vals = {
                    'date': payment_vals.get('date'),
                    'partner_id': payment_vals.get('partner_id'),
                    'partner_type': payment_vals.get('partner_type'),
                    'payment_type': payment_vals.get('payment_type'),
                    'company_id': payment_vals.get('company_id'),
                    'journal_id': line.journal_id.id,
                    'payment_method_line_id': line.payment_method_line_id.id,
                    'amount': line.amount,
                    'currency_id': self.company_currency_id.id,
                }
                # Talonario del hijo (si tiene)
                if line.receiptbook_id:
                    child_vals['receiptbook_id'] = line.receiptbook_id.id
                    
                link_payment_vals.append(Command.create(child_vals))
            
            # Agregar los pagos hijos al principal
            payment_vals['link_payment_ids'] = link_payment_vals
            
        return payment_vals

    def action_create_payments(self):
        """
        Override para asegurar compatibilidad con payment_bundle.
        El módulo l10n_ar_payment_bundle maneja la creación de link_payment_ids
        automáticamente cuando se setea en los vals.
        """
        return super().action_create_payments()
