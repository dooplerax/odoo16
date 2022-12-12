# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountBankReconcile(models.Model):
    _inherit = 'account.payment'
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),
                              ('not_payment', 'No Cobrado')],
                             readonly=True, default='draft', copy=False, string="Status")

    def nocobrado(self):
        for rec in self:

            if rec.state != 'draft':
                raise UserError(
                    _("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            rec.write({'state': 'not_payment'})
