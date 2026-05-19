from odoo import fields, models, api


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l16n_ec_is_internal = fields.Boolean(string='Is internal L16N EC', compute='_compute_is_internal')

    @api.depends('move_type')
    def _compute_is_internal(self):
        for record in self:
            if record.move_type == 'in_invoice':
                record.l16n_ec_is_internal = False
            if record.move_type == 'out_invoice':
                record.l16n_ec_is_internal = True

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        if move:
            res['l16n_ec_invoice_origin_id'] = move.id
        return res


