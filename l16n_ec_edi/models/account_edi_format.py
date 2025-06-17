from odoo import fields, models, api


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _check_move_configuration(self, move):
        if move.display_name:
            move._compute_l10n_latam_document_number()
        return super()._check_move_configuration(move)
