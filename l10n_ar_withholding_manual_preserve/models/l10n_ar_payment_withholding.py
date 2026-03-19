from odoo import api, fields, models


class L10nArPaymentWithholding(models.Model):
    _inherit = "l10n_ar.payment.withholding"

    # Flag to indicate if the amount was manually edited
    manual_amount = fields.Boolean(
        string="Manual Amount",
        default=False,
        help="Indicates if the withholding amount was manually edited by the user",
    )

    # Store the original computed amount for comparison
    original_computed_amount = fields.Monetary(
        string="Original Computed Amount",
        help="The amount as originally computed by the system",
    )

    @api.depends("base_amount", "tax_id")
    def _compute_amount(self):
        """Override to preserve manual amounts"""
        for line in self.filtered(lambda r: r.payment_id.partner_type == "supplier"):
            # If manual_amount flag is set, don't recalculate
            if line.manual_amount and line.amount:
                continue
            
            tax_id = line._get_withholding_tax()
            if not tax_id:
                line.amount = 0.0
                line.ref = False
            else:
                tax_amount, __, __, ref = line._tax_compute_all_helper()
                line.amount = tax_amount
                line.original_computed_amount = tax_amount
                line.ref = ref

    def write(self, vals):
        """Detect manual amount changes and set the flag"""
        if 'amount' in vals and 'manual_amount' not in vals:
            for line in self:
                # If the amount is being changed and it's different from computed
                if line.original_computed_amount and vals['amount'] != line.original_computed_amount:
                    vals['manual_amount'] = True
        return super().write(vals)
