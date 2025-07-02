from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'


    l16n_ec_invoice_origin_id = fields.Many2one(comodel_name='account.move', string='Factura origen')

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        if self.move_type in ('out_refund', 'in_refund') and self.l16n_ec_invoice_origin_id:
            lines = self.line_ids | self.l16n_ec_invoice_origin_id.line_ids
            lines_to_reconcile = lines.filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable', 'liability_payable'))
            if lines_to_reconcile:
                lines_to_reconcile.reconcile()
        return res
