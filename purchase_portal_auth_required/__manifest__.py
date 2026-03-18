# -*- coding: utf-8 -*-
{
    'name': 'Purchase Portal Authentication Required',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Require authentication to view purchase orders in portal (removes access token bypass)',
    'description': """
Purchase Portal Authentication Required
=======================================

This module enhances security for purchase order portal access by:

* Requiring user authentication to view purchase orders
* Removing the access_token bypass that allows unauthenticated access
* Redirecting unauthenticated users to the login page

**Problem solved:**
When sending a purchase order by email, Odoo includes a "View Order" button with an 
access_token in the URL. This allows anyone with the link to view the order without 
authentication, which can be a security risk.

**Solution:**
This module overrides the portal controller to always require authentication,
regardless of whether a valid access_token is provided.

**Note:** After installing this module, vendors will need to have a portal account
and be logged in to view their purchase orders.
    """,
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'portal',
    ],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
