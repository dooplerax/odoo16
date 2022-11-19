from odoo import fields, models

class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ec_retention_entity = fields.Char(string="Emission Retention Entity", size=3, default="001")
    l10n_ec_retention_emission = fields.Char(string="Emission Retencion Point", size=3, default="001")
    


