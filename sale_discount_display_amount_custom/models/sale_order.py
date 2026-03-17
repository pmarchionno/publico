# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    display_discount_with_tax = fields.Boolean(
        name="Show the Discount with TAX",
        help="Check this field to show the Discount with TAX",
        related="company_id.display_discount_with_tax",
    )
    discount_total = fields.Monetary(
        compute="_compute_discount_total",
        name="Discount total",
        currency_field="currency_id",
        store=True,
    )
    discount_subtotal = fields.Monetary(
        compute="_compute_discount_total",
        name="Discount Subtotal",
        currency_field="currency_id",
        store=True,
    )
    price_subtotal_no_discount = fields.Monetary(
        compute="_compute_discount_total",
        name="Subtotal Without Discount",
        currency_field="currency_id",
        store=True,
    )
    price_total_no_discount = fields.Monetary(
        compute="_compute_discount_total",
        name="Total Without Discount",
        currency_field="currency_id",
        store=True,
    )

    @api.model
    def _get_compute_discount_total_depends(self):
        return [
            "order_line.discount_total",
            "order_line.discount_subtotal",
            "order_line.price_subtotal_no_discount",
            "order_line.price_total_no_discount",
        ]

    @api.depends(lambda self: self._get_compute_discount_total_depends())
    def _compute_discount_total(self):
        for order in self:
            discount_total = sum(order.order_line.mapped("discount_total"))
            discount_subtotal = sum(order.order_line.mapped("discount_subtotal"))
            price_subtotal_no_discount = sum(
                order.order_line.mapped("price_subtotal_no_discount")
            )
            price_total_no_discount = sum(
                order.order_line.mapped("price_total_no_discount")
            )
            order.update(
                {
                    "discount_total": discount_total,
                    "discount_subtotal": discount_subtotal,
                    "price_subtotal_no_discount": price_subtotal_no_discount,
                    "price_total_no_discount": price_total_no_discount,
                }
            )

    def _get_discount_display_vals(self):
        self.ensure_one()
        show_tax_included = bool(self.display_discount_with_tax)
        discount_amount = self.discount_total if show_tax_included else self.discount_subtotal
        total_without_discount_amount = (
            self.price_total_no_discount
            if show_tax_included
            else self.price_subtotal_no_discount
        )
        current_total_amount = self.amount_total if show_tax_included else self.amount_untaxed
        return {
            "discount_amount": discount_amount,
            "discount_label": _("Discount (Tax incl.)") if show_tax_included else _("Discount"),
            "show_discount": bool(discount_amount),
            "show_tax_included": show_tax_included,
            "show_total_without_discount": (
                self.company_id.report_total_without_discount
                and total_without_discount_amount != current_total_amount
            ),
            "total_without_discount_amount": total_without_discount_amount,
            "total_without_discount_label": (
                _("Total Without Discount")
                if show_tax_included
                else _("Subtotal Without Discount")
            ),
        }
