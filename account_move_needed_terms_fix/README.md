# Account Move Needed Terms Fix

## Problem

When confirming payments with withholdings (especially Argentine withholdings using `l10n_ar_withholding`), Odoo throws the following error:

```
TypeError: 'bool' object is not subscriptable
File: /odoo/addons/account/models/account_move.py, line 1360
invoice.needed_terms[key]['balance'] += values['balance']
```

## Cause

The computed field `needed_terms` (type `fields.Binary`) sometimes returns `False` instead of a dictionary. The original code assumes it's always a dict and fails when trying to access it.

## Solution

This module overrides the `_compute_needed_terms` method to add `isinstance` checks before accessing `needed_terms` as a dictionary.

## Installation

1. Copy this module to your Odoo addons directory
2. Update the app list
3. Install the module

## Compatibility

- Odoo 18.0
- Tested with `l10n_ar_withholding` module

## Author

- Hitofusion (https://www.hitofusion.com)

## License

LGPL-3
