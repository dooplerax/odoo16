from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ec_retention_entity = fields.Char(string="Emission Retention Entity", size=3, default="001")
    l10n_ec_retention_emission = fields.Char(string="Emission Retencion Point", size=3, default="001")

    account_bank_retention = fields.Many2one('account.account',
                                             string='Cuenta de movimiento retención tarjeta de crédito',
                                             domain=[('deprecated', '=', False)])

    billing_location = fields.Many2one('billing.location', string='Accounting Location', stored=True)

class Users(models.Model):
    _inherit = 'res.users'

    billing_location = fields.Many2one('billing.location', string='Accounting Location', stored=True)

class BillingLocation(models.Model):
    _name = 'billing.location'
    _description = 'Custom Address Model'

    street = fields.Char(string='Street', stored="True")
    street2 = fields.Char(string='Street2', stored="True")
    zip = fields.Char(string='Zip', stored="True")
    city = fields.Char(string='City', stored="True")
    state_id = fields.Many2one("res.country.state", string='State', stored="True")
    country_id = fields.Many2one('res.country', string='Country', stored="True")

    location = fields.Char(string='Location', compute='_compute_location', store=True)

    @api.depends('street', 'street2', 'zip', 'city', 'state_id', 'country_id')
    def _compute_location(self):
        for record in self:
            location_parts = [record.street or '', record.street2 or '', record.city or '', record.state_id.name or '',
                               record.country_id.name or '']
            record.location = '/ '.join(filter(None, location_parts))

    def name_get(self):
        result = []
        for record in self:
            name = record.location
            result.append((record.id, name))
        return result

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('move_type')
    def _compute_journal_id(self):
        for record in self:
            user_billing_location = self.env.user.billing_location.location
            suitable_journals = self.env['account.journal'].search(
                [('billing_location.location', '=', user_billing_location)])
            if suitable_journals:
                record.journal_id = suitable_journals[0].id
                continue

            if record.journal_id.type not in record._get_valid_journal_types():
                record.journal_id = record._search_default_journal()

