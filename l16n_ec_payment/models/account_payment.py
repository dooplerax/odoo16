from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    payment_number = fields.Char('Número', default='000')


class AccountMove(models.Model):
    _inherit = 'account.move'
    payment_number = fields.Char('Número', default='000')

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="Payment Method (SRI)",
        default=lambda self: self._get_default_payment_method(),
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.l10n_ec_sri_payment_id = self._get_default_payment_method()

    def _get_default_payment_method(self):
        sri_payment = self.env['l10n_ec.sri.payment'].search([('name', '=', 'Otros con utilización del sistema financiero')],limit=1)
        return sri_payment.id or False
