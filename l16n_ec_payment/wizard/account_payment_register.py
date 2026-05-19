from odoo import fields, models, api
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    payment_number = fields.Char('Número', copy=False)
    type_journal = fields.Selection(related='journal_id.type', string='Tipo de Diario', readonly=True, store=True)

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)
        payment_vals['payment_number'] = self.payment_number
        payment_vals['invoice_date'] = self.payment_date
        return payment_vals

    @api.depends(
        'can_edit_wizard',
        'source_amount',
        'source_amount_currency',
        'source_currency_id',
        'company_id',
        'currency_id',
    )
    def _compute_amount(self):
        for wiz in self:
            if not wiz.amount:
                if wiz.source_currency_id and wiz.can_edit_wizard:
                    batch = wiz._get_batches()[0]
                    wiz.amount = wiz._get_total_amount_in_wizard_currency_to_full_reconcile(batch)[0]
                else:
                    wiz.amount = None
            continue

    def action_create_payments(self):
        if self.journal_id and self.payment_number:
            account_payments = self.env['account.payment'].search([
                ('journal_id', '=', self.journal_id.id),
                ('payment_number', '=', self.payment_number)
            ])
            if len(account_payments) > 0:
                raise UserError(
                    f'Ya existe un pago con el diario {self.journal_id.name} y con el número {self.payment_number} creado.'
                )
        return super(AccountPaymentRegister, self).action_create_payments()
