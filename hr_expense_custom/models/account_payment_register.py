# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command


class AccountPaymentRegister(models.TransientModel):
    """
    Hereda el wizard de registro de pago para agregar:
    1. Campo de Talonario de Recibo (receiptbook_id) - campo propio del wizard
    2. Soporte para Pagos Múltiples (payment_bundle) con líneas de pago
    
    NOTA: El campo receiptbook_id NO existe en account.payment.register por defecto.
    El módulo account_payment_pro_receiptbook solo lo define en account.payment.
    Nosotros lo agregamos aquí como campo transient para permitir seleccionarlo
    en el wizard y propagarlo al pago creado.
    """
    _inherit = 'account.payment.register'

    # === Campo Talonario de Recibo ===
    # El modelo account.payment.receiptbook tiene: company_id, partner_type
    # NO tiene journal_id (ese campo solo existe en account.payment)
    receiptbook_id = fields.Many2one(
        'account.payment.receiptbook',
        string='Talonario de Recibo',
        check_company=True,
        domain="[('company_id', '=', company_id), ('partner_type', '=', partner_type)]",
    )

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
                lambda m: hasattr(m, 'expense_sheet_id') and m.expense_sheet_id
            )
            wizard.is_from_expense = bool(expense_moves)

    @api.depends('payment_method_line_id')
    def _compute_is_payment_bundle(self):
        """Detecta si el método de pago es 'payment_bundle' (Pagos Múltiples)."""
        for wizard in self:
            wizard.is_payment_bundle = (
                wizard.payment_method_line_id and
                wizard.payment_method_line_id.payment_method_id.code == 'payment_bundle'
            )

    @api.depends('payment_line_ids.amount', 'amount')
    def _compute_payment_lines_total(self):
        """Calcula el total de las líneas de pago y la diferencia con el monto a pagar."""
        for wizard in self:
            total = sum(wizard.payment_line_ids.mapped('amount'))
            wizard.payment_lines_total = total
            wizard.payment_lines_difference = wizard.amount - total

    # === Onchange ===
    
    @api.onchange('journal_id', 'partner_type')
    def _onchange_journal_id_receiptbook(self):
        """Auto-seleccionar talonario por defecto cuando cambia el diario."""
        if self.company_id and self.partner_type:
            receiptbook = self.env['account.payment.receiptbook'].search([
                ('company_id', '=', self.company_id.id),
                ('partner_type', '=', self.partner_type),
            ], limit=1)
            self.receiptbook_id = receiptbook if receiptbook else False

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
        
        # Propagar receiptbook_id si fue seleccionado
        if self.receiptbook_id:
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
                    'payment_method_line_id': line.payment_method_line_id.id if line.payment_method_line_id else False,
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
