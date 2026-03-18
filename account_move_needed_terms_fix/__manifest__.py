# -*- coding: utf-8 -*-
{
    'name': 'Account Move Needed Terms Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix for needed_terms field returning False instead of dict',
    'description': """
Account Move Needed Terms Fix
=============================

This module fixes a bug in Odoo's account module where the computed field
`needed_terms` sometimes returns `False` instead of a dictionary, causing
a `TypeError: 'bool' object is not subscriptable` when confirming payments
with withholdings.

**Bug:** When confirming a payment (especially with Argentine withholdings),
the `_compute_needed_terms` method fails because it assumes `needed_terms`
is always a dict, but it can be `False` in some edge cases.

**Fix:** Added isinstance checks before accessing `needed_terms` as a dict.

**Tested on:** Odoo 18.0 with l10n_ar_withholding module.
    """,
    'author': 'Hitofusion',
    'website': 'https://www.hitofusion.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
