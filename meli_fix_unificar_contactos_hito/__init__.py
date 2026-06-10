# -*- coding: utf-8 -*-

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    """
    Hook post-instalación: ejecutar limpieza inicial de contactos duplicados
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Buscar contactos duplicados y unificarlos
    env['res.partner']._unificar_contactos_duplicados_inicial()