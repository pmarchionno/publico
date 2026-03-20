# © 2026 Hitofusion
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class StockBackorderConfirmation(models.TransientModel):
    """
    Fix: El método process() original devolvía una tupla (res, print_action)
    cuando res era un dict, lo cual confundía al cliente web.
    Ahora devuelve solo la acción de impresión.
    """
    _inherit = "stock.backorder.confirmation"

    def process(self):
        res = super().process()
        pickings = (
            self.env["stock.picking"]
            .browse(self._context.get("picking_ids"))
            .filtered("book_required")
        )
        if pickings and not self.env.context.get("active_model") == "stock.picking.batch":
            # FIX: Retornar solo la acción de impresión, no una tupla
            return pickings.do_print_voucher()
        return res

    def process_cancel_backorder(self):
        res = super().process_cancel_backorder()
        pickings = (
            self.env["stock.picking"]
            .browse(self._context.get("picking_ids"))
            .filtered("book_required")
        )
        if pickings:
            return pickings.do_print_voucher()
        return res
