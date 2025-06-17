##
##
from odoo import fields, models
class AccountPaymentRegister(models.TransientModel):
    _inherit ='account.payment.register'

    payment_number = fields.Char('Número', copy=False)
    type_journal = fields.Selection(related='journal_id.type', string='Tipo de Diario', readonly=True, store=True)


    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)
        payment_vals['payment_number'] = self.payment_number
        payment_vals['invoice_date'] = self.payment_date
        return payment_vals