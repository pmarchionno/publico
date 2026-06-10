# -*- coding: utf-8 -*-
##############################################################################
#
#    Módulo para unificar contactos duplicados de MercadoLibre
#    Copyright (C) 2026 HITOFUSION
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################

{
    'name': 'MercadoLibre Fix - Unificar Contactos Duplicados',
    'summary': 'Unifica contactos duplicados generados por meli_oerp cuando son la misma persona',
    'version': '18.0.1.0.0',
    'author': 'HITOFUSION',
    'website': 'https://www.hitofusion.com',
    "category": "Sales",
    "depends": ['base', 'sale', 'meli_oerp'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'wizard/unificar_contactos_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'AGPL-3',
    'post_init_hook': 'post_init_hook',
}