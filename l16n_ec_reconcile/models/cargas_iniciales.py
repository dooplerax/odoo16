# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas


from odoo import api, fields, models


class SaldosInicialesModel(models.Model):
    _name = 'bnc.initial.balances'
    _description = "Cheques girados y no cobrados"

    date = fields.Date('Fecha')
    number = fields.Char('Numero de Cheque')
    partner_id = fields.Many2one('res.partner', 'Proveedor')
    value = fields.Float('Monto')
    concepto = fields.Char('Concepto')

    conciliate = fields.Boolean('Conciliado', default=False)
    conciliate_date = fields.Date('Fecha de Conciliacion')

    account_id = fields.Many2one(
        'account.account',
        'Cuenta',
        required=True,
        domain=[('internal_type', '=', 'liquidity')]
    )
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, change_default=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice')
    )
