from odoo import models, Command
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def copy(self, default=None):
        """
        Fix for MissingError when creating debit notes with copy_lines.
        
        The original account_ux module tries to clean inactive taxes from
        copied lines, but some lines may be deleted during _sync_dynamic_lines().
        
        This override safely handles the case where lines no longer exist.
        """
        res = super().copy(default=default)
        
        # Safely clean inactive taxes from copied lines
        # Re-fetch line_ids to get only existing records
        existing_line_ids = res.line_ids.exists()
        
        for line_to_clean in existing_line_ids.filtered(
            lambda x: x.tax_ids and False in x.mapped("tax_ids.active")
        ):
            try:
                inactive_taxes = line_to_clean.tax_ids.filtered(lambda x: not x.active)
                if inactive_taxes:
                    line_to_clean.tax_ids = [
                        Command.unlink(x.id) for x in inactive_taxes
                    ]
            except Exception as e:
                _logger.warning(
                    "Could not clean inactive taxes from line %s: %s",
                    line_to_clean.id, str(e)
                )
                continue
        
        # Call _onchange_partner_commercial if exists (from account_ux)
        if hasattr(res, '_onchange_partner_commercial'):
            res._onchange_partner_commercial()
        
        return res
