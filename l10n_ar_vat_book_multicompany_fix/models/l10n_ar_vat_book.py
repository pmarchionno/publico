# -*- coding: utf-8 -*-
from odoo import api, models


class L10nArVatBook(models.AbstractModel):
    _inherit = 'l10n_ar.vat.book'

    @api.model
    def _vat_book_get_lines_domain(self, options):
        """
        Fix multi-company filter for VAT Book ZIP export.
        
        Original issue: Used self.env.company.ids which only returns the current
        user's company, ignoring companies selected in the report filter.
        
        Solution: Get company_ids from options['companies'] to match XLSX behavior.
        """
        # FIX: Obtener compañías desde options en lugar de self.env.company
        # Esto alinea el comportamiento del ZIP con el XLSX que ya funciona bien
        company_ids = [comp['id'] for comp in options.get('companies', [])] or self.env.company.ids
        
        selected_journal_types = self._vat_book_get_selected_tax_types(options)
        
        domain = [
            ('journal_id.type', 'in', selected_journal_types),
            ('journal_id.l10n_latam_use_documents', '=', True),
            ('company_id', 'in', company_ids),
        ]
        
        # Filtro de estado (posted o all)
        state = options.get('all_entries') and 'all' or 'posted'
        if state and state.lower() != 'all':
            domain += [('state', '=', state)]
        
        # Filtro de fechas
        if options.get('date').get('date_to'):
            domain += [('date', '<=', options['date']['date_to'])]
        if options.get('date').get('date_from'):
            domain += [('date', '>=', options['date']['date_from'])]
        
        return domain
