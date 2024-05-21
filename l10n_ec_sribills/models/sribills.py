# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>

import logging
from odoo import fields, models, api, _

from datetime import datetime
from datetime import date
from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)

class SriBills(models.Model):
    # taba sri_bills
    _name = 'sri.bills'
    __logger = logging.getLogger(_name)

    comprobante = fields.Char('Num. Retención')
    serie_comprobante = fields.Char('SRI Comprobante')
    ruc_emisor = fields.Char('RUC Emisor')
    razon_social_emisor = fields.Char('Razón Social Emisor')
    fecha_emision = fields.Char('Fecha Emisión')
    fecha_autorizacion = fields.Char('Fecha Autorización')
    tipo_emision = fields.Char('Tipo Emisión')
    identificacion_receptor = fields.Char('Identificación Receptor')
    clave_acceso = fields.Char('Clave Acceso')
    numero_autorizacion = fields.Char('Número de Autorización')
    importe_total = fields.Char('Importe Total')
    generada = fields.Boolean('Descargada')
    sribill_id = fields.Many2one('sri.bills.load', 'Carga')
    documento_firmado = fields.Text('xml SRI')
    comentario = fields.Char('Detalle')
    existing_invoice_id = fields.Many2one('account.move', string="Factura Existente")

    def unlink(self):
        raise ValidationError("No se permite eliminar registros despues de una importación.")