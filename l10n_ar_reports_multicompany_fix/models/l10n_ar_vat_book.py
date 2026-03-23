# -*- coding: utf-8 -*-
from odoo import api, models


class L10nArTaxReportHandler(models.AbstractModel):
    _inherit = "l10n_ar.tax.report.handler"

    @api.model
    def _vat_book_get_lines_domain(self, options):
        """
        Override to fix multi-company support for ZIP export.
        
        Original code uses self.env.company.ids which only returns the current
        company, ignoring the companies selected in the report options.
        
        This fix uses get_report_company_ids(options) to get all selected
        companies, aligning the ZIP export behavior with the XLSX export.
        """
        # FIX: Use selected companies from options instead of current company only
        company_ids = self.get_report_company_ids(options)
        
        selected_journal_types = self._vat_book_get_selected_tax_types(options)
        domain = [
            ("journal_id.type", "in", selected_journal_types),
            ("journal_id.l10n_latam_use_documents", "=", True),
            ("company_id", "in", company_ids)
        ]
        
        state = options.get("all_entries") and "all" or "posted"
        if state and state.lower() != "all":
            domain += [("state", "=", state)]
        
        if options.get("date", {}).get("date_to"):
            domain += [("date", "<=", options["date"]["date_to"])]
        
        if options.get("date", {}).get("date_from"):
            domain += [("date", ">=", options["date"]["date_from"])]
        
        return domain
