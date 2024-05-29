from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import models, fields, api, _, Command

class AccountMoveInvoiceLine(models.Model):
    _name = 'account.move.invoice.line'

    move_id = fields.Many2one('account.move', string='Move', stored=True)
    account_id = fields.Many2one('account.account', string='Cuenta', stored=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', stored=True)
    label = fields.Char(string='Etiqueta', stored=True)
    debit = fields.Monetary(string='Débito', currency_field='currency_id', stored=True)
    credit = fields.Monetary(string='Crédito', currency_field='currency_id', stored=True)
    currency_id = fields.Many2one('res.currency', string='Currency')

    move_id = fields.Many2one('account.move', string='Account Move', stored=True)
