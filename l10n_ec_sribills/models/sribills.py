# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>

import logging
from odoo import fields, models, api, _

from datetime import datetime
from datetime import date

class SriBills(models.Model):
    # taba sri_bills
    _name = 'sri.bills'
    __logger = logging.getLogger(_name)

    comprobante = fields.Char('Num. Retención')
    serie_comprobante = fields.Char('Sri Comprobante')
    ruc_emisor = fields.Char('Ruc Emisor')
    razon_social_emisor = fields.Char('Razon Social Emisor')
    fecha_emision = fields.Char('Fecha Emisión')
    fecha_autorizacion = fields.Char('Fecha Autorización')
    tipo_emision = fields.Char('Tipo Emisión')
    identificacion_receptor = fields.Char('Identificación Receptor')
    clave_acceso = fields.Char('Clave Acceso')
    numero_autorizacion = fields.Char('Numero Autiruzación')
    importe_total = fields.Char('Importe Total')
    generada = fields.Boolean('Descargada')
    sribill_id = fields.Many2one('sri.bills.load', 'Carga')
    documento_firmado = fields.Text('xml sri')
    comentario = fields.Char('Detalle')