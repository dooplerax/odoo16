# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 18/10/2022
# Requerimiento:

import time
from datetime import datetime

from odoo import api, fields, models,_
from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)


class AccountAtsDoc(models.Model):
    _name = 'account.ats.doc'
    _description = 'Tipos Comprobantes Autorizados'

    code = fields.Char('Código', size=2, required=True)
    name = fields.Char('Tipo Comprobante', size=64, required=True)


class AccountAtsSustento(models.Model):
    _name = 'account.ats.sustento'
    _description = 'Sustento del Comprobante'


    @api.depends('code', 'type')
    def name_get(self):
        """
         Nombre
        :return:
        """
        res = []
        for record in self:
            name = '%s - %s' % (record.code, record.type)
            res.append((record.id, name))
        return res

    _rec_name = 'type'

    code = fields.Char('Código', size=2, required=True)
    type = fields.Char('Tipo de Sustento', size=128, required=True)

#
# class AccountAuthorisation(models.Model):
#     _name = 'account.authorisation'
#     _order = 'expiration_date desc'
#
#     @api.multi
#     @api.depends('type_id', 'num_start', 'num_end')
#     def name_get(self):
#         """
#         Nombre
#         :return:
#         """
#         res = []
#         for record in self:
#             name = u'%s. estab: (%s-%s) serie: (%s-%s) ' % (
#                 record.type_id.code,
#                 record.serie_entidad,
#                 record.serie_emision,
#                 record.num_start,
#                 record.num_end
#             )
#             res.append((record.id, name))
#         return res
#
#     @api.one
#     @api.depends('expiration_date')
#     def _compute_active(self):
#         """
#         Calcula si esta activo el documento con las fechas
#         :return:
#         """
#         if self.is_electronic:
#             self.active = True
#         if not self.expiration_date:
#             return
#         now = datetime.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d')
#         due_date = datetime.strptime(self.expiration_date, '%Y-%m-%d')
#         self.active = now < due_date
#
#     def _get_type(self):
#         return self._context.get('type', 'in_invoice')  # pylint: disable=E1101
#
#     def _get_in_type(self):
#         return self._context.get('in_type', 'externo')
#
#     def _get_partner(self):
#         """
#         Calcula el partnet
#         :return:
#         """
#         partner = self.env.user.company_id.partner_id
#         if self._context.get('partner_id'):
#             partner = self._context.get('partner_id')
#         return partner
#
#     @api.model
#     @api.returns('self', lambda value: value.id)
#     def create(self, values):
#         """
#         modica el create
#         :param values:
#         :return:
#         """
#         res = self.search([('partner_id', '=', values['partner_id']),
#                            ('type_id', '=', values['type_id']),
#                            ('serie_entidad', '=', values['serie_entidad']),
#                            ('serie_emision', '=', values['serie_emision']),
#                            ('serie_emision', '=', values['serie_emision']),
#                            ('active', '=', True)])
#         if res:
#             MSG = u'Ya existe una autorización activa para %s' % values['type_id']
#             raise ValidationError(MSG)
#
#         partner_id = self.env.user.company_id.partner_id.id
#         if values['partner_id'] == partner_id:
#             typ = self.env['account.ats.doc'].browse(values['type_id'])
#             name_type = '{0}_{1}'.format(values['name'], values['type_id'])
#             if values['num_start'] == 0 or not values['num_start']:
#                 values['num_start'] =1
#             sequence_data = {
#                 'code': typ.code == '07' and 'account.retention' or 'account.invoice',  # noqa
#                 'name': name_type,
#                 'padding': 9,
#                 'number_next': values['num_start'],
#             }
#             seq = self.env['ir.sequence'].create(sequence_data)
#             values.update({'sequence_id': seq.id})
#         return super(AccountAuthorisation, self).create(values)
#
#     @api.multi
#     def unlink(self):
#         """
#         Modifica el eliminar
#         :return:
#         """
#         inv = self.env['account.invoice']
#         res = inv.search([('auth_inv_id', '=', self.id)])
#         if res:
#             raise UserError(
#                 'Esta autorización esta relacionada a un documento.'
#             )
#         return super(AccountAuthorisation, self).unlink()
#
#     name = fields.Char('Num. de Autorización', size=128)
#     serie_entidad = fields.Char('Serie Entidad', size=3, required=True)
#     serie_emision = fields.Char('Serie Emision', size=3, required=True)
#     num_start = fields.Integer('Desde')
#     num_end = fields.Integer('Hasta')
#     is_electronic = fields.Boolean('Documento Electrónico ?')
#     expiration_date = fields.Date('Fecha de Vencimiento')
#     active = fields.Boolean(
#         compute='_compute_active',
#         string='Activo',
#         store=True,
#         default=True
#     )
#     in_type = fields.Selection(
#         [('interno', 'Internas'),
#          ('externo', 'Externas')],
#         string='Tipo Interno',
#         readonly=True,
#         change_default=True,
#         default=_get_in_type
#     )
#     type_id = fields.Many2one(
#         'account.ats.doc',
#         'Tipo de Comprobante',
#         required=True
#     )
#     partner_id = fields.Many2one(
#         'res.partner',
#         'Empresa',
#         required=True,
#         default=_get_partner
#     )
#
#     company_id = fields.Many2one(
#         'res.company',
#         'Company',
#         required=True,
#         change_default=True,
#         readonly=True,
#         states={'draft': [('readonly', False)]},
#         default=lambda self: self.env.user.company_id.id  # noqa
#     )
#
#     sequence_id = fields.Many2one(
#         'ir.sequence',
#         'Secuencia',
#         help='Secuencia Alfanumerica para el documento, se debe registrar cuando pertenece a la compañia',  # noqa
#         ondelete='cascade'
#     )
#
#     _sql_constraints = [
#         ('number_unique',
#          'unique(partner_id,expiration_date,type_id)',
#          u'La relación de autorización, serie entidad, serie emisor y tipo, debe ser única.'),  # noqa
#     ]
#
#     def is_valid_number(self, number):
#         """
#         Metodo que verifica si @number esta en el rango
#         de [@num_start,@num_end]
#         """
#         if self.is_electronic:
#             return True
#         if self.num_start <= number <= self.num_end:
#             return True
#         return False
#
