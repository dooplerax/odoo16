from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l16n_ec_invoice_origin_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura origen'
    )

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)

        for move in self:
            if move.move_type in ('out_refund', 'in_refund') and move.l16n_ec_invoice_origin_id:
                lines = move.line_ids | move.l16n_ec_invoice_origin_id.line_ids
                lines_to_reconcile = lines.filtered(
                    lambda line: line.account_id.reconcile and
                                 line.account_id.account_type in ('asset_receivable', 'liability_payable')
                )
                if lines_to_reconcile:
                    lines_to_reconcile.reconcile()
        return res