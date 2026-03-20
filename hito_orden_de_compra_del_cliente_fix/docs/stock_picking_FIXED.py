# ARCHIVO CORREGIDO PARA hito_orden_de_compra_del_cliente/models/stock_picking.py
# Copiar este contenido al archivo original del módulo del cliente
# 
# FIX: Se eliminó el override de button_validate() que causaba remitos duplicados
# Fecha: 2026-03-20
# Ticket: Food Novelty

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
    )

    invoice_print = fields.Char(
        string="impresión de facturas", compute="compute_invoice_print"
    )

    orden_compra_cliente = fields.Char(
        tracking=True,
        string="Orden de Compra del Cliente",
        related="sale_order_id.orden_compra_cliente",
        store=True,
        readonly=True,
    )

    invoice_ids = fields.Many2many(
        "account.move",
        string="Facturas",
        widget="many2many_tags",
        compute="_get_invoices",
    )

    def get_move_line_ids(self):
        move_line_ids = {}

        for move_line in self.move_line_ids:
            product = move_line.product_id
            if product.id not in move_line_ids:
                move_line_ids[product.id] = {
                    "name": product.name,
                    "qty_done": move_line.qty_done,
                    "default_code": product.default_code,
                    "uom_name": move_line.product_uom_id.name,
                }
            else:
                move_line_ids[product.id]["qty_done"] += move_line.qty_done

        return list(move_line_ids.values())

    def _get_invoices(self):
        invoice_ids = []
        for picking in self:
            if picking.sale_id:
                sale_order = picking.sale_id
                if sale_order.invoice_ids:
                    invoice_ids.extend(sale_order.invoice_ids.ids)
        if invoice_ids:
            self.invoice_ids = [(6, 0, invoice_ids)]
        else:
            self.invoice_ids = [(6, 0, [])]

    def compute_invoice_print(self):
        for rec in self:
            invoices = []
            for inv in rec.invoice_ids:
                if inv.name not in invoices:
                    invoices.append(inv.name)
            if invoices:
                res = ",".join(invoices)
            else:
                res = ""
        rec.invoice_print = res

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if res.picking_type_code == "outgoing":
            if "origin" in res:
                order = self.env["sale.order"].search([("name", "=", res[0].origin)])
                if order and order.orden_compra_cliente:
                    res.orden_compra_cliente = order.orden_compra_cliente
        return res

    @api.onchange("sale_order_id")
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            self.orden_compra_cliente = self.sale_order_id.orden_compra_cliente
        else:
            self.orden_compra_cliente = False

    # ==========================================================================
    # FIX HITOFUSION 2026-03-20:
    # ==========================================================================
    # - ELIMINADO override de button_validate() que causaba:
    #   1. Bloqueo del wizard por ValidationError prematuro
    #   2. Duplicación de assign_numbers() (ya se llama en _action_done de stock_voucher)
    # 
    # - La validación de book_id ya se hace en stock_voucher.do_stock_voucher_transfer_check()
    # - La asignación de números ya se hace en stock_voucher._action_done()
    # 
    # NO AGREGAR button_validate() AQUÍ - stock_voucher ya maneja todo
    # ==========================================================================
