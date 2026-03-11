# Copyright 2018 ACSONE SA/NV
# Copyright 2026 Hito Fusion - Fix for Odoo 17 hook signatures
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import api, SUPERUSER_ID
from odoo.tools.sql import column_exists, create_column

_logger = logging.getLogger(__name__)

COLUMNS = (
    ("sale_order", "price_subtotal_no_discount"),
    ("sale_order", "price_total_no_discount"),
    ("sale_order", "discount_total"),
    ("sale_order", "discount_subtotal"),
    ("sale_order_line", "price_subtotal_no_discount"),
    ("sale_order_line", "price_total_no_discount"),
    ("sale_order_line", "discount_total"),
    ("sale_order_line", "discount_subtotal"),
)


def _get_cr(cr_or_env):
    """Get cursor from cr or env (handles both Odoo 17 hook signatures)"""
    if hasattr(cr_or_env, 'cr'):
        # It's an Environment, get the cursor
        return cr_or_env.cr
    # It's already a cursor
    return cr_or_env


def pre_init_hook(cr_or_env):
    """Pre-init hook - handles both cr and env signatures"""
    cr = _get_cr(cr_or_env)
    for table, column in COLUMNS:
        if not column_exists(cr, table, column):
            _logger.info("Create discount column %s in database", column)
            create_column(cr, table, column, "numeric")


def post_init_hook(cr_or_env, registry=None):
    """Post-init hook - handles both (cr, registry) and (env) signatures"""
    cr = _get_cr(cr_or_env)
    _logger.info("Compute discount columns")

    # Set default values for records without discount
    query = """
    UPDATE sale_order_line
    SET
        price_subtotal_no_discount = price_subtotal,
        price_total_no_discount = price_total,
        discount_total = 0,
        discount_subtotal = 0
    WHERE discount = 0.0 OR discount IS NULL
    """
    cr.execute(query)

    query = """
    UPDATE sale_order
    SET
        price_subtotal_no_discount = amount_untaxed,
        price_total_no_discount = amount_total,
        discount_total = 0,
        discount_subtotal = 0
    """
    cr.execute(query)

    # Compute for orders with discounts using ORM
    query = """
    SELECT DISTINCT order_id FROM sale_order_line WHERE discount > 0.0;
    """
    cr.execute(query)
    order_ids = [row[0] for row in cr.fetchall()]

    if order_ids:
        # Get or create environment
        if hasattr(cr_or_env, 'cr'):
            env = cr_or_env
        else:
            env = api.Environment(cr, SUPERUSER_ID, {})
        orders = env["sale.order"].browse(order_ids)
        orders.mapped("order_line")._update_discount_display_fields()
