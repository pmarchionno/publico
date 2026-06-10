# -*- coding: utf-8 -*-
##############################################################################
#
#    Módulo para unificar contactos duplicados de MercadoLibre
#    Copyright (C) 2026 HITOFUSION
#
##############################################################################

import logging
import unicodedata
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campos para tracking
    meli_unificado_desde = fields.Many2one(
        'res.partner',
        string='Unificado desde',
        help='Indica que este contacto fue creado a partir de la unificación de otro',
        readonly=True,
    )
    meli_contacto_unificado = fields.Boolean(
        string='Contacto unificado',
        default=False,
        help='Indica que este contacto es resultado de una unificación',
    )

    # -------------------------------------------------------------------------
    # Métodos de normalización
    # -------------------------------------------------------------------------

    @api.model
    def _normalizar_nombre(self, nombre):
        """
        Normaliza un nombre para comparación:
        - Minúsculas
        - Sin acentos
        - Sin espacios extra
        """
        if not nombre:
            return ''
        nombre = nombre.lower().strip()
        # Quitar acentos
        nombre = unicodedata.normalize('NFD', nombre)
        nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
        # Normalizar espacios
        nombre = re.sub(r'\s+', ' ', nombre)
        return nombre

    @api.model
    def _extraer_apellidos(self, nombre):
        """
        Extrae apellidos de un nombre completo.
        Asume formato: "Nombre Apellido1 Apellido2" o "Apellido1 Apellido2, Nombre"
        """
        nombre_norm = self._normalizar_nombre(nombre)
        if not nombre_norm:
            return []
        
        # Separar por espacios y filtrar palabras comunes
        palabras = nombre_norm.split()
        palabras_comunes = {'de', 'la', 'del', 'los', 'las', 'y', 'e', 'i', 'o', 'a'}
        
        # Filtrar palabras comunes y muy cortas (posiblemente iniciales)
        apellidos = [p for p in palabras 
                     if len(p) > 2 and p not in palabras_comunes]
        
        return apellidos

    @api.model
    def _nombres_son_similares(self, nombre1, nombre2, umbral=0.6):
        """
        Determina si dos nombres son similares basándose en:
        - Coincidencia de apellidos
        - Similitud de dirección
        """
        if not nombre1 or not nombre2:
            return False
        
        # Normalizar
        norm1 = self._normalizar_nombre(nombre1)
        norm2 = self._normalizar_nombre(nombre2)
        
        # Si son idénticos, son similares
        if norm1 == norm2:
            return True
        
        # Extraer apellidos
        apellidos1 = set(self._extraer_apellidos(nombre1))
        apellidos2 = set(self._extraer_apellidos(nombre2))
        
        if not apellidos1 or not apellidos2:
            return False
        
        # Calcular intersección
        interseccion = apellidos1 & apellidos2
        union = apellidos1 | apellidos2
        
        if not union:
            return False
        
        ratio = len(interseccion) / len(union)
        
        # Si comparten al menos un apellido principal (no común)
        if len(interseccion) >= 1 and ratio >= umbral:
            return True
        
        return False

    @api.model
    def _direcciones_son_similares(self, partner1, partner2):
        """
        Compara si dos direcciones son similares
        """
        if not partner1.street or not partner2.street:
            return False
        
        # Normalizar calles
        calle1 = self._normalizar_nombre(partner1.street)
        calle2 = self._normalizar_nombre(partner2.street)
        
        # Extraer números
        numeros1 = set(re.findall(r'\d+', calle1))
        numeros2 = set(re.findall(r'\d+', calle2))
        
        # Si comparten el mismo número, es muy probable que sea la misma dirección
        if numeros1 and numeros2 and numeros1 & numeros2:
            return True
        
        # Comparar similitud de texto
        palabras1 = set(calle1.split())
        palabras2 = set(calle2.split())
        
        if not palabras1 or not palabras2:
            return False
        
        interseccion = palabras1 & palabras2
        union = palabras1 | palabras2
        
        if not union:
            return False
        
        ratio = len(interseccion) / len(union)
        
        return ratio >= 0.5

    # -------------------------------------------------------------------------
    # Métodos de unificación
    # -------------------------------------------------------------------------

    @api.model
    def _buscar_contacto_principal_para_unificar(self, partner):
        """
        Busca un contacto principal existente que podría ser la misma persona
        que el contacto dado.
        
        Criterios de búsqueda:
        1. Mismo VAT/CUIT
        2. Nombres similares + dirección similar
        """
        if not partner:
            return False
        
        # 1. Buscar por VAT
        if partner.vat:
            # Buscar contactos con el mismo VAT que no sean de tipo invoice/delivery
            mismo_vat = self.search([
                ('vat', '=', partner.vat),
                ('id', '!=', partner.id),
                ('type', 'in', ['contact', False]),
            ], limit=1, order='id asc')
            
            if mismo_vat:
                _logger.info(
                    "Unificación por VAT: %s (id:%s) → %s (id:%s)",
                    partner.name, partner.id,
                    mismo_vat.name, mismo_vat.id
                )
                return mismo_vat
        
        # 2. Buscar por nombre similar + dirección similar
        # Solo para contactos de MercadoLibre (que tengan meli_buyer_id o similar)
        if hasattr(partner, 'meli_buyer_id') and partner.meli_buyer_id:
            # Buscar contactos principales con nombre similar
            candidatos = self.search([
                ('id', '!=', partner.id),
                ('type', 'in', ['contact', False]),
                ('is_company', '=', False),
            ])
            
            for candidato in candidatos:
                if self._nombres_son_similares(partner.name, candidato.name):
                    if self._direcciones_son_similares(partner, candidato):
                        _logger.info(
                            "Unificación por nombre+dirección: %s (id:%s) → %s (id:%s)",
                            partner.name, partner.id,
                            candidato.name, candidato.id
                        )
                        return candidato
        
        return False

    @api.model
    def _unificar_contacto(self, partner_destino, partner_origen):
        """
        Unifica dos contactos:
        - partner_destino: el contacto que se mantiene (principal)
        - partner_origen: el contacto que se absorbe
        
        Acciones:
        1. Transferir datos fiscales del origen al destino (si no los tiene)
        2. Actualizar órdenes de venta para que apunten al destino
        3. Marcar el origen como unificado
        4. Crear un contacto hijo de tipo invoice si es necesario
        """
        if not partner_destino or not partner_origen:
            return False
        
        if partner_destino.id == partner_origen.id:
            return False
        
        _logger.info("Iniciando unificación: %s (id:%s) absorbe %s (id:%s)",
                     partner_destino.name, partner_destino.id,
                     partner_origen.name, partner_origen.id)
        
        # 1. Transferir VAT si el destino no lo tiene
        if partner_origen.vat and not partner_destino.vat:
            try:
                partner_destino.write({'vat': partner_origen.vat})
                _logger.info("VAT transferido: %s", partner_origen.vat)
            except Exception as e:
                _logger.warning("No se pudo transferir VAT: %s", e)
        
        # 2. Transferir datos fiscales argentinos si existen
        campos_fiscales = [
            'l10n_ar_afip_responsibility_type_id',
            'l10n_latam_identification_type_id',
            'afip_responsability_type_id',
            'property_account_position_id',
            'partner_document_type_id',
        ]
        
        vals_fiscales = {}
        for campo in campos_fiscales:
            if campo in partner_origen._fields and campo in partner_destino._fields:
                if getattr(partner_origen, campo) and not getattr(partner_destino, campo):
                    vals_fiscales[campo] = getattr(partner_origen, campo).id
        
        if vals_fiscales:
            try:
                partner_destino.write(vals_fiscales)
                _logger.info("Datos fiscales transferidos: %s", list(vals_fiscales.keys()))
            except Exception as e:
                _logger.warning("No se pudieron transferir datos fiscales: %s", e)
        
        # 3. Actualizar órdenes de venta
        sale_order_obj = self.env['sale.order']
        ordenes = sale_order_obj.search([
            '|', '|',
            ('partner_id', '=', partner_origen.id),
            ('partner_invoice_id', '=', partner_origen.id),
            ('partner_shipping_id', '=', partner_origen.id),
        ])
        
        for orden in ordenes:
            vals = {}
            if orden.partner_id.id == partner_origen.id:
                vals['partner_id'] = partner_destino.id
            if orden.partner_invoice_id.id == partner_origen.id:
                vals['partner_invoice_id'] = partner_destino.id
            if orden.partner_shipping_id.id == partner_origen.id:
                vals['partner_shipping_id'] = partner_destino.id
            
            if vals:
                try:
                    orden.write(vals)
                except Exception as e:
                    _logger.warning("Error actualizando orden %s: %s", orden.name, e)
        
        _logger.info("Órdenes actualizadas: %s", len(ordenes))
        
        # 4. Marcar el origen como unificado
        try:
            partner_origen.write({
                'active': False,
                'meli_contacto_unificado': True,
                'meli_unificado_desde': partner_destino.id,
            })
            _logger.info("Contacto origen marcado como unificado")
        except Exception as e:
            _logger.warning("Error marcando contacto como unificado: %s", e)
        
        return True

    @api.model
    def _unificar_contactos_duplicados_inicial(self):
        """
        Método para ejecutar al instalar el módulo.
        Busca y unifica contactos duplicados existentes.
        """
        _logger.info("Iniciando limpieza de contactos duplicados...")
        
        # Buscar contactos de facturación de MercadoLibre que podrían estar duplicados
        # Criterio: contactos de tipo 'invoice' con meli_buyer_partner_id
        contactos_invoice = self.search([
            ('type', '=', 'invoice'),
            ('active', '=', True),
        ])
        
        unificados = 0
        for contacto in contactos_invoice:
            # Buscar si hay un contacto principal similar
            principal = self._buscar_contacto_principal_para_unificar(contacto)
            
            if principal:
                if self._unificar_contacto(principal, contacto):
                    unificados += 1
        
        _logger.info("Limpieza completada. Contactos unificados: %s", unificados)
        
        return unificados