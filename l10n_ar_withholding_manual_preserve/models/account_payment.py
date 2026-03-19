from odoo import api, fields, models, Command


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("l10n_ar_fiscal_position_id", "partner_id", "company_id", "date")
    def _compute_l10n_ar_withholding_line_ids(self):
        """Override to preserve manually edited withholding lines.
        
        The original method clears all lines with Command.clear() every time
        the compute runs. This override preserves lines where the user has
        manually edited the amount.
        """
        for rec in self.filtered(lambda x: x.partner_type == "supplier"):
            date = rec.date or fields.Date.today()
            
            # Get existing lines that were manually edited
            manual_lines = rec.l10n_ar_withholding_line_ids.filtered(
                lambda l: l.manual_amount and l.amount
            )
            manual_tax_ids = manual_lines.mapped('tax_id.id')
            
            # Get the taxes that should be applied based on fiscal position
            expected_taxes = self.env['account.tax']
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                expected_taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                    rec.partner_id, rec.company_id, date, "withholding"
                )
            
            # Build commands list
            withholdings = []
            
            # Remove lines that are not in expected taxes AND not manually edited
            lines_to_remove = rec.l10n_ar_withholding_line_ids.filtered(
                lambda l: l.tax_id.id not in expected_taxes.ids and not l.manual_amount
            )
            for line in lines_to_remove:
                withholdings.append(Command.delete(line.id))
            
            # Add new taxes that don't exist yet (and are not manually handled)
            existing_tax_ids = rec.l10n_ar_withholding_line_ids.mapped('tax_id.id')
            for tax in expected_taxes:
                if tax.id not in existing_tax_ids:
                    withholdings.append(Command.create({"tax_id": tax.id}))
            
            # Only apply commands if there are changes
            if withholdings:
                rec.l10n_ar_withholding_line_ids = withholdings
            
            # Remove auto-computed lines with zero amount (but not manual ones)
            to_remove = rec.l10n_ar_withholding_line_ids.filtered(
                lambda wth: wth.amount == 0 
                and wth.tax_id.l10n_ar_tax_type not in ["earnings", "earnings_scale"]
                and not wth.manual_amount
            )
            if to_remove:
                rec.l10n_ar_withholding_line_ids -= to_remove
