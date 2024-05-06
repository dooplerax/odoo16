from odoo import fields, models, api

class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ec_retention_entity = fields.Char(string="Emission Retention Entity", size=3, default="001")
    l10n_ec_retention_emission = fields.Char(string="Emission Retencion Point", size=3, default="001")

    account_bank_retention = fields.Many2one('account.account',
                                             string='Cuenta de movimiento retención tarjeta de crédito',
                                             domain=[('deprecated', '=', False)])

    def _get_accounting_locations(self):
        # Esta función devuelve las opciones para el campo de selección accounting_location
        return [('', 'Seleccionar'),('quito', 'Quito'), ('cuenca', 'Cuenca'), ('guayaquil', 'Guayaquil')]

    accounting_location = fields.Selection(_get_accounting_locations, string='Accounting Location', stored=True)

class Users(models.Model):
    _inherit = 'res.users'

    def _get_accounting_locations(self):
        # Esta función devuelve las opciones para el campo de selección accounting_location
        return [('', 'Seleccionar'),('quito', 'Quito'), ('cuenca', 'Cuenca'), ('guayaquil', 'Guayaquil')]

    accounting_location = fields.Selection(_get_accounting_locations, string='Accounting Location', stored = True)

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('move_type')
    def _compute_journal_id(self):
        for record in self:
            user_accounting_location = self.env.user.accounting_location
            suitable_journals = self.env['account.journal'].search(
                [('accounting_location', '=', user_accounting_location)])
            if suitable_journals:
                record.journal_id = suitable_journals[0].id
                continue

            if record.journal_id.type not in record._get_valid_journal_types():
                record.journal_id = record._search_default_journal()

