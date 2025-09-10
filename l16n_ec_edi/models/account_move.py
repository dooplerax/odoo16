from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l16n_ec_invoice_origin_id = fields.Many2one(comodel_name='account.move', string='Factura origen')
    retention_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='retention_line_id',
        string="Líneas de la retención",
    )
    have_invoices = fields.Boolean(string="Tiene facturas?", store=False, compute='_compute_have_invoices')

    @api.depends('name')
    def _compute_have_invoices(self):
        self.have_invoices = len(self.line_ids.mapped('l10n_ec_withhold_invoice_id').ids) > 0

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        for move in self:
            if move.move_type in ('out_refund', 'in_refund') and move.l16n_ec_invoice_origin_id:
                lines = move.line_ids | move.l16n_ec_invoice_origin_id.line_ids
                lines_to_reconcile = lines.filtered(
                    lambda line: line.account_id.reconcile and line.account_id.account_type in (
                        'asset_receivable',
                        'liability_payable'
                    )
                )
                if lines_to_reconcile:
                    lines_to_reconcile.reconcile()
        return res

    def write(self, vals):
        if vals.get('retention_line_ids'):
            for retention_line in vals['retention_line_ids']:
                if retention_line[2]:
                    retention_line[2]['move_id'] = self.id
                    if retention_line[2].get('tax_ids'):
                        tax_id = self.env['account.tax'].search([('id', '=', retention_line[2]['tax_ids'][0][2][0])])
                        account_id = False
                        for invoice_repartition_line_id in tax_id.invoice_repartition_line_ids:
                            if invoice_repartition_line_id.account_id:
                                account_id = invoice_repartition_line_id.account_id.id
                        retention_line[2]['account_id'] = account_id
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        retention_lines = {'retention_line_ids': False}
        are_there_retention_lines = False
        for val in vals_list:
            if val.get('retention_line_ids'):
                are_there_retention_lines = True
                retention_lines['retention_line_ids'] = val['retention_line_ids']
                del val['retention_line_ids']
        record = super().create(vals_list)
        if are_there_retention_lines:
            record.write(retention_lines)
        return record


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    retention_line_id = fields.Many2one(comodel_name='account.move', string="Invoice")
    ret_tax_amount = fields.Monetary(string="Importe del impuesto")

    @api.depends('tax_ids')
    def _compute_withhold_tax_amount(self):
        lines_ids = self.filtered('move_id.l10n_ec_withhold_type')
        invoices = lines_ids.mapped('l10n_ec_withhold_invoice_id').ids
        for line in lines_ids:
            currency_rate = line.balance / line.amount_currency if line.amount_currency != 0 else 1
            line.l10n_ec_withhold_tax_amount = (
                line.currency_id.round(currency_rate * abs(line.price_total - line.price_subtotal))
                if invoices else line.ret_tax_amount
            )
        (self - lines_ids).l10n_ec_withhold_tax_amount = 0.0
