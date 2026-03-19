from odoo import models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        """
        Override para corregir la generación de remitos duplicados.
        
        PROBLEMA ORIGINAL:
        El método en hito_orden_de_compra_del_cliente llamaba a assign_numbers()
        después del super(), pero stock_voucher ya lo hace en _action_done().
        Esto causaba que se generaran 2 remitos en entregas parciales.
        
        SOLUCIÓN:
        Solo validamos que exista el libro de remitos antes de validar.
        La asignación de números la hace stock_voucher automáticamente.
        
        Fix por Jinzo - 2026-03-19
        """
        # Validar que tenga libro de remitos antes de validar
        for picking in self:
            if picking.book_required and not picking.book_id:
                raise ValidationError(
                    "Debe seleccionar un libro de remitos antes de validar el picking."
                )
        # Ejecutar la función original - stock_voucher._action_done() asignará los números
        # IMPORTANTE: NO llamar a assign_numbers() aquí, eso lo hace stock_voucher
        return super(StockPicking, self).button_validate()
