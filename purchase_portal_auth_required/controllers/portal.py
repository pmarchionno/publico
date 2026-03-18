# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.purchase.controllers.portal import CustomerPortal


class CustomerPortalAuthRequired(CustomerPortal):
    """
    Override purchase order portal controller to require authentication.
    
    This removes the access_token bypass, ensuring that users must be
    logged in to view purchase orders, even if they have a valid token.
    """

    def _purchase_order_check_access(self, order_id, access_token=None):
        """
        Override to always require authentication.
        
        The original method allows access if a valid access_token is provided.
        This override ignores the token and always requires the user to be
        authenticated and have proper access rights.
        """
        # Check if user is authenticated (not public user)
        if request.env.user._is_public():
            # Redirect to login - will be handled by the route decorator
            return None
        
        # Get the order without sudo to enforce access rights
        order = request.env['purchase.order'].browse(order_id)
        
        # Check if order exists and user has access
        if not order.exists():
            return None
            
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except Exception:
            return None
            
        return order

    @http.route([
        '/my/purchase/<int:order_id>',
        '/my/purchase/<int:order_id>/<access_token>',
    ], type='http', auth='user', website=True)
    def portal_my_purchase_order(self, order_id, access_token=None, **kw):
        """
        Override to require 'user' auth instead of 'public'.
        
        By changing auth='public' to auth='user', Odoo will automatically
        redirect unauthenticated users to the login page.
        
        The access_token parameter is kept for URL compatibility but is ignored.
        """
        order = self._purchase_order_check_access(order_id, access_token=None)
        
        if not order:
            return request.redirect('/my')
        
        # Get report URL without access token
        report_url = '/my/purchase/%s/pdf' % order_id
        
        values = {
            'order': order,
            'report_type': 'html',
            'report_url': report_url,
            'page_name': 'purchase',
        }
        
        return request.render('purchase.portal_my_purchase_order', values)

    @http.route([
        '/my/purchase/<int:order_id>/pdf',
        '/my/purchase/<int:order_id>/pdf/<access_token>',
    ], type='http', auth='user', website=True)
    def portal_my_purchase_order_report(self, order_id, access_token=None, **kw):
        """
        Override PDF download to require authentication.
        """
        order = self._purchase_order_check_access(order_id, access_token=None)
        
        if not order:
            return request.redirect('/my')
        
        # Generate PDF report
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'purchase.report_purchaseorder',
            [order_id]
        )
        
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'inline; filename="%s.pdf"' % order.name),
        ]
        
        return request.make_response(pdf_content, headers=headers)
