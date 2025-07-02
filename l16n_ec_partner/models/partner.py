# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 29/03/2021
# Requerimiento: P00038

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..lib.validators import validate_cedula, validate_ruc

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'name')
    def name_get(self):
        """
        to string
        :return:
        """
        data = []
        for partner in self:
            display_val = u'{0} '.format(
                partner.name
            )
            data.append((partner.id, display_val))
        return data

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        """
        Busqueda por nombre
        :param name:
        :param args:
        :param operator:
        :param limit:
        :return:
        """

        if not args:
            args = []
        if name:
            partners = self.search([('vat', operator, name)] + args, limit=limit)  # noqa
            if not partners:
                partners = self.search([('name', operator, name)] + args, limit=limit)  # noqa
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()

    # @api.constrains('vat')
    # def _check_identifier(self):
    #
    #     """
    #     Valida la identificacion
    #     :return:
    #     """
    #     for obj in self:
    #         if not obj.vat:
    #             raise ValidationError('Número de Identificación campo requerido')
    #         if obj.l10n_latam_identification_type_id.name != 'Pasaporte':
    #             partner = self.search(
    #                 [('vat', '=', obj.vat),
    #                  ('company_id', '=', obj.env.user.company_id.id),
    #                  ('id', '!=', obj.id)])
    #             if len(partner) > 0:
    #                 raise ValidationError('Cliente registrado en el sistema')
    #         res = False
    #         if obj.l10n_latam_identification_type_id.name == 'Cédula':
    #             res = validate_cedula(obj.vat)
    #         elif obj.l10n_latam_identification_type_id.name == 'RUC':
    #             res = validate_ruc(obj.vat)
    #         else:
    #             return True
    #         if not res:
    #             raise ValidationError('Número de Identificación incorrecto.')

    @api.constrains("vat", "country_id", "l10n_latam_identification_type_id")
    def check_vat(self):
        it_ruc = self.env.ref("l10n_ec.ec_ruc", False)
        it_dni = self.env.ref("l10n_ec.ec_dni", False)
        ecuadorian_partners = self.filtered(
            lambda x: x.country_id == self.env.ref("base.ec")
        )
        # for partner in ecuadorian_partners:
        #     if partner.vat:
        #         if partner.l10n_latam_identification_type_id.id in (
        #                 it_ruc.id,
        #                 it_dni.id,
        #         ):
        #             if partner.l10n_latam_identification_type_id.id == it_dni.id and len(partner.vat) != 10:
        #                 raise ValidationError(_('If your identification type is %s, it must be 10 digits')
        #                                       % it_dni.display_name)
        #             if partner.l10n_latam_identification_type_id.id == it_ruc.id and len(partner.vat) != 13:
        #                 raise ValidationError(_('If your identification type is %s, it must be 13 digits')
        #                                       % it_ruc.display_name)
        return super(ResPartner, self - ecuadorian_partners).check_vat()

    @api.depends('vat')
    def _person_type_compute(self):
        """
        Determina el tio de persona por la cedula
        :return:
        """
        for obj in self:
            if not obj.vat:
                obj.person_type = '0'
            elif int(obj.vat[2]) <= 6:
                obj.person_type = '6'
            elif int(obj.vat[2]) in [6, 9]:
                obj.person_type = '9'
            else:
                obj.person_type = '0'

    person_type = fields.Selection(
        compute='_person_type_compute',
        selection=[
            ('6', 'Persona Natural'),
            ('9', 'Persona Juridica'),
            ('0', 'Otro')
        ],
        string='Persona',
        store=True
    )

    @api.constrains('vat', 'l10n_latam_identification_type_id', 'company_id')
    def _check_unique_identification_per_company(self):
        """
        Se dispara al crear/editar un partner. Valida que NO exista otro partner
        (distinto al actual) con el mismo vat (número de identificación) y la misma
        company_id, incluso cuando company_id es False (sin compañía).
        """

        if self.env.context.get('skip_identification_constraint'):
            return

        for partner in self:
            # Si no hay vat, no hay nada que comparar
            if not partner.vat:
                continue

            # Búsqueda de otro partner con mismo vat y misma company_id (puede ser False)
            otro = self.search([
                ('vat', '=', partner.vat),
                ('company_id', '=', partner.company_id.id),
                ('id', '!=', partner.id),
            ], limit=1)

            if otro:
                # Mensaje de error más genérico para incluir casos sin compañía
                if partner.company_id:
                    msg = _(
                        "Ya existe un contacto con el mismo Número de Identificación "
                        "(%s) en la compañía %s."
                    ) % (partner.vat, partner.company_id.name)
                else:
                    msg = _(
                        "Ya existe un contacto con el mismo Número de Identificación "
                        "(%s) sin compañía asignada."
                    ) % partner.vat
                raise ValidationError(msg)

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def _check_identification_length(self):
        """
        Valida que:
          - Si el tipo de identificación es RUC, el vat tenga 13 dígitos numéricos.
          - Si es Cédula, el vat tenga 10 dígitos numéricos.
        Los tipos 'RUC' y 'Cédula' se obtienen por external ID.
        """
        # Cambia 'tu_módulo.ec_ruc' y 'tu_módulo.ec_dni' por tus XML IDs reales.
        ruc_type = self.env.ref('l10n_ec.ec_ruc', raise_if_not_found=False)
        dni_type = self.env.ref('l10n_ec.ec_dni', raise_if_not_found=False)

        for partner in self:
            if not partner.vat or not partner.l10n_latam_identification_type_id:
                continue

            tipo = partner.l10n_latam_identification_type_id

            if ruc_type and tipo.id == ruc_type.id:
                # RUC → 13 dígitos numéricos
                if len(partner.vat) != 13 or not partner.vat.isdigit():
                    raise ValidationError(_(
                        "El campo 'Número de identificación' para un RUC debe "
                        "contener exactamente 13 dígitos numéricos."
                    ))

            if dni_type and tipo.id == dni_type.id:
                # Cédula → 10 dígitos numéricos
                if len(partner.vat) != 10 or not partner.vat.isdigit():
                    raise ValidationError(_(
                        "El campo 'Número de identificación' para una cédula debe "
                        "contener exactamente 10 dígitos numéricos."
                    ))


class ResCompany(models.Model):
    _inherit = 'res.company'

    tradename = fields.Char('Nombre Comercial', size=500)

    type_invoice = fields.Selection([('1', 'Electrónica'), ('2', 'Manual')], string='Tipo Facturación',
                                    required=True, default='1')
    special_taxpayer = fields.Selection(
        [
            ('NO', 'No'),
            ('Contribuyente Especial', 'Contribuyente Especial'),
            ('Régimen Microempresas', 'Régimen Microempresas'),
            ('CONTRIBUYENTE RÉGIMEN RIMPE', 'CONTRIBUYENTE RÉGIMEN RIMPE'),
            ('Régimen General', 'Régimen General')
        ],
        string='Contribuyente ',
        required=True,
        default='NO'
    )
    retention_agent = fields.Selection(
        [
            ('SI', 'SI'),
            ('NO', 'NO')
        ],
        string='Agente de Retención',
        default='NO'
    )


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def action_merge(self):
        self = self.with_context(skip_identification_constraint=True)
        return super(MergePartnerAutomatic, self).action_merge()