# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.tools import frozendict

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('invoice_payment_term_id', 'invoice_date', 'currency_id', 'amount_total_in_currency_signed', 'invoice_date_due')
    def _compute_needed_terms(self):
        """
        Override to fix TypeError when needed_terms is False instead of dict.
        Also ensures needed_terms is ALWAYS assigned for all records.
        
        CRITICAL FIX: Iterate over self directly, not self.with_context()
        The with_context creates a new recordset and assignments may not propagate.
        """
        _logger.info("=== _compute_needed_terms called for %s records: %s ===", len(self), self.ids)
        AccountTax = self.env['account.tax']
        
        # CRITICAL FIX: Iterate over self directly, not self.with_context()
        for invoice in self:
            try:
                _logger.info("Processing move %s (type: %s)", invoice.id, invoice.move_type)
                
                # ALWAYS initialize needed_terms as empty dict FIRST
                invoice.needed_terms = {}
                invoice.needed_terms_dirty = True
                _logger.info("Assigned needed_terms={} to move %s", invoice.id)
                
                # Only process invoices with lines
                if not (invoice.is_invoice(True) and invoice.invoice_line_ids):
                    _logger.info("Move %s is not an invoice or has no lines, skipping", invoice.id)
                    continue
                
                # Get invoice with bin_size=False for binary field access
                invoice_ctx = invoice.with_context(bin_size=False)
                is_draft = invoice_ctx.id != invoice_ctx._origin.id
                sign = 1 if invoice_ctx.is_inbound(include_receipts=True) else -1
                
                if invoice.invoice_payment_term_id:
                    if is_draft:
                        tax_amount_currency = 0.0
                        tax_amount = tax_amount_currency
                        untaxed_amount_currency = 0.0
                        untaxed_amount = untaxed_amount_currency
                        sign = invoice_ctx.direction_sign
                        base_lines, _tax_lines = invoice_ctx._get_rounded_base_and_tax_lines(round_from_tax_lines=False)
                        AccountTax._add_accounting_data_in_base_lines_tax_details(
                            base_lines, 
                            invoice.company_id, 
                            include_caba_tags=invoice_ctx.always_tax_exigible
                        )
                        tax_results = AccountTax._prepare_tax_lines(base_lines, invoice.company_id)
                        for base_line, to_update in tax_results['base_lines_to_update']:
                            untaxed_amount_currency += sign * to_update['amount_currency']
                            untaxed_amount += sign * to_update['balance']
                        for tax_line_vals in tax_results['tax_lines_to_add']:
                            tax_amount_currency += sign * tax_line_vals['amount_currency']
                            tax_amount += sign * tax_line_vals['balance']
                    else:
                        tax_amount_currency = invoice.amount_tax * sign
                        tax_amount = invoice.amount_tax_signed
                        untaxed_amount_currency = invoice.amount_untaxed * sign
                        untaxed_amount = invoice.amount_untaxed_signed
                    
                    invoice_payment_terms = invoice.invoice_payment_term_id._compute_terms(
                        date_ref=invoice.invoice_date or invoice.date or fields.Date.context_today(invoice),
                        currency=invoice.currency_id,
                        tax_amount_currency=tax_amount_currency,
                        tax_amount=tax_amount,
                        untaxed_amount_currency=untaxed_amount_currency,
                        untaxed_amount=untaxed_amount,
                        company=invoice.company_id,
                        cash_rounding=invoice.invoice_cash_rounding_id,
                        sign=sign
                    )
                    
                    for term_line in invoice_payment_terms['line_ids']:
                        key = frozendict({
                            'move_id': invoice.id,
                            'date_maturity': fields.Date.to_date(term_line.get('date')),
                            'discount_date': invoice_payment_terms.get('discount_date'),
                        })
                        values = {
                            'balance': term_line['company_amount'],
                            'amount_currency': term_line['foreign_amount'],
                            'discount_date': invoice_payment_terms.get('discount_date'),
                            'discount_balance': invoice_payment_terms.get('discount_balance') or 0.0,
                            'discount_amount_currency': invoice_payment_terms.get('discount_amount_currency') or 0.0,
                        }
                        if not isinstance(invoice.needed_terms, dict):
                            invoice.needed_terms = {}
                        if key not in invoice.needed_terms:
                            invoice.needed_terms[key] = values
                        elif isinstance(invoice.needed_terms.get(key), dict):
                            invoice.needed_terms[key]['balance'] += values['balance']
                            invoice.needed_terms[key]['amount_currency'] += values['amount_currency']
                        else:
                            invoice.needed_terms[key] = values
                else:
                    # No payment term - use invoice_date_due
                    if not isinstance(invoice.needed_terms, dict):
                        invoice.needed_terms = {}
                    invoice.needed_terms[frozendict({
                        'move_id': invoice.id,
                        'date_maturity': fields.Date.to_date(invoice.invoice_date_due),
                        'discount_date': False,
                        'discount_balance': 0.0,
                        'discount_amount_currency': 0.0
                    })] = {
                        'balance': invoice.amount_total_signed,
                        'amount_currency': invoice.amount_total_in_currency_signed,
                    }
                
                _logger.info("Finished processing move %s", invoice.id)
            
            except Exception as e:
                _logger.error("Exception processing move %s: %s", invoice.id, str(e))
                # Still assign empty dict on error to prevent cascade failure
                invoice.needed_terms = {}
                invoice.needed_terms_dirty = True
                raise
