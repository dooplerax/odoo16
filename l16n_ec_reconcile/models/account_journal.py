# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    template_reconcilie = fields.Selection(
        [('select', 'Seleccion'),('pichincha', 'Pichincha'), ('pacifico', 'Podubanco')],
        default='select', copy=False, string="Conciliación")
