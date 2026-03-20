# © 2026 Hitofusion
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def do_print_voucher(self):
        """
        Override para agregar close_on_report_download.
        Esto cierra el wizard automáticamente cuando se descarga el PDF.
        """
        result = self.env.ref("stock.action_report_delivery").report_action(self)
        result['close_on_report_download'] = True
        return result
