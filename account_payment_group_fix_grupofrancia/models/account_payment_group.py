# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'
    
    # ✅ Sobrescribir el campo para forzar recálculo en tiempo real
    selected_debt = fields.Monetary(
        string='Selected Debt',
        compute='_compute_selected_debt',
        store=False,  # ⚠️ CLAVE: No almacenar, siempre recalcular
        currency_field='currency_id',
    )
    
    @api.depends('to_pay_move_line_ids.amount_residual')
    def _compute_selected_debt(self):
        """
        Calcula la suma de todos los comprobantes seleccionados.
        Se ejecuta automáticamente cada vez que cambian las líneas.
        """
        for rec in self:
            _logger.debug(
                "FIX GF | _compute_selected_debt | PG=%s | lines=%s",
                rec.name or 'draft',
                len(rec.to_pay_move_line_ids),
            )
            
            # Sumar todos los importes residuales
            total = sum(rec.to_pay_move_line_ids.mapped('amount_residual'))
            
            # Aplicar signo según el tipo de partner
            sign = -1.0 if rec.partner_type == 'supplier' else 1.0
            rec.selected_debt = total * sign
            
            _logger.debug(
                "FIX GF | selected_debt=%s | total=%s | sign=%s",
                rec.selected_debt,
                total,
                sign,
            )
    
    @api.onchange('to_pay_move_line_ids')
    def _onchange_to_pay_move_lines_refresh_debt(self):
        """
        Fuerza la actualización del campo selected_debt cuando se modifican
        las líneas desde la interfaz (agregar/eliminar comprobantes).
        
        Esto asegura que el campo se actualice INMEDIATAMENTE en la pantalla
        sin necesidad de guardar el registro.
        """
        self._compute_selected_debt()
        _logger.debug(
            "FIX GF | onchange triggered | PG=%s | selected_debt=%s",
            self.name or 'draft',
            self.selected_debt,
        )
