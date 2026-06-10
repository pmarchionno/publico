# -*- coding: utf-8 -*-
##############################################################################
#
#    Módulo para unificar contactos duplicados de MercadoLibre
#    Copyright (C) 2026 HITOFUSION
#
##############################################################################

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UnificarContactosWizard(models.TransientModel):
    _name = 'meli_fix_unificar_contactos_hito.unificar_contactos_wizard'
    _description = 'Wizard para unificar contactos duplicados de MercadoLibre'

    # Campos
    modo_ejecucion = fields.Selection([
        ('simulacion', 'Simulación (solo muestra resultados)'),
        ('real', 'Ejecución real (unifica contactos)'),
    ], string='Modo de ejecución', default='simulacion', required=True)

    criterio_unificacion = fields.Selection([
        ('vat', 'Solo mismo VAT/CUIT'),
        ('nombre_direccion', 'Nombre similar + Dirección similar'),
        ('ambos', 'Ambos criterios (recomendado)'),
    ], string='Criterio de unificación', default='ambos', required=True)

    resultado = fields.Text(
        string='Resultado',
        readonly=True,
    )

    contactos_encontrados = fields.Integer(
        string='Contactos encontrados',
        readonly=True,
        default=0,
    )

    contactos_unificados = fields.Integer(
        string='Contactos unificados',
        readonly=True,
        default=0,
    )

    # -------------------------------------------------------------------------
    # Métodos principales
    # -------------------------------------------------------------------------

    def action_buscar_contactos(self):
        """
        Busca contactos duplicados según el criterio seleccionado
        """
        self.ensure_one()
        
        partner_obj = self.env['res.partner']
        
        # Buscar contactos de facturación activos
        contactos_invoice = partner_obj.search([
            ('type', '=', 'invoice'),
            ('active', '=', True),
        ])
        
        encontrados = 0
        detalle = []
        
        for contacto in contactos_invoice:
            # Buscar contacto principal similar
            principal = partner_obj._buscar_contacto_principal_para_unificar(contacto)
            
            if principal:
                encontrados += 1
                detalle.append(
                    f"• {contacto.name} (id:{contacto.id}) → {principal.name} (id:{principal.id})"
                )
        
        self.contactos_encontrados = encontrados
        
        if detalle:
            self.resultado = f"Contactos encontrados para unificar: {encontrados}\n\n"
            self.resultado += "\n".join(detalle[:50])  # Limitar a 50 para no saturar
            if len(detalle) > 50:
                self.resultado += f"\n... y {len(detalle) - 50} más"
        else:
            self.resultado = "No se encontraron contactos duplicados."
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'meli_fix_unificar_contactos_hito.unificar_contactos_wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_unificar_contactos(self):
        """
        Ejecuta la unificación de contactos
        """
        self.ensure_one()
        
        if self.modo_ejecucion == 'simulacion':
            raise UserError(_(
                "Estás en modo simulación. Cambia a 'Ejecución real' para unificar contactos."
            ))
        
        partner_obj = self.env['res.partner']
        
        # Buscar contactos de facturación activos
        contactos_invoice = partner_obj.search([
            ('type', '=', 'invoice'),
            ('active', '=', True),
        ])
        
        unificados = 0
        errores = []
        
        for contacto in contactos_invoice:
            # Buscar contacto principal similar
            principal = partner_obj._buscar_contacto_principal_para_unificar(contacto)
            
            if principal:
                try:
                    if partner_obj._unificar_contacto(principal, contacto):
                        unificados += 1
                except Exception as e:
                    errores.append(f"Error con {contacto.name}: {str(e)}")
        
        self.contactos_unificados = unificados
        
        self.resultado = f"Unificación completada.\n\n"
        self.resultado += f"Contactos unificados: {unificados}\n"
        
        if errores:
            self.resultado += f"\nErrores ({len(errores)}):\n"
            self.resultado += "\n".join(errores[:10])
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'meli_fix_unificar_contactos_hito.unificar_contactos_wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_cerrar(self):
        """
        Cierra el wizard
        """
        return {'type': 'ir.actions.act_window_close'}