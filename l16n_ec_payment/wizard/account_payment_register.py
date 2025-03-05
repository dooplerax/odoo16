##
##
from odoo import fields, models
class AccountPaymentRegister(models.TransientModel):
    _inherit ='account.payment.register'

    payment_number = fields.Char('Número', default='000', copy=False)

    _sql_constraints = [
        ('unique_payment_number', 'unique(payment_number)', 'El número de pago debe ser único.')
    ]

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)
        payment_vals['payment_number'] = self.payment_number
        return payment_vals