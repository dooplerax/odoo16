##
##
from odoo import fields, models
class AccountPaymentRegister(models.TransientModel):
    _inherit ='account.payment.register'

    payment_number = fields.Char('Número', default='000')

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)
        payment_vals['payment_number'] = self.payment_number
        return payment_vals