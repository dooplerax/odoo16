from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    payment_number = fields.Char('Número', default='000')


class AccountMove(models.Model):
    _inherit = 'account.move'
    payment_number = fields.Char('Número', default='000')
