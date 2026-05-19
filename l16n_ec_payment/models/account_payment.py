from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date
from odoo.tools import date_utils


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_number = fields.Char('Número')
    type_journal = fields.Selection(related='journal_id.type', string='Tipo de Diario', readonly=True, store=True)

    def _synchronize_from_moves(self, changed_fields):
        """ Update the account_payment regarding its related account.move.
        Also, check both models are still consistent
        :param changed_fields: A set containing all modified fields on account.move.
        """
        if self._context.get('skip_account_move_synchronization'):
            return
        for pay in self.with_context(skip_account_move_synchronization=True):
            if pay.move_id.statement_line_id:
                continue
            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}
            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))
            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
                if len(counterpart_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one receivable/payable account (with an exception of "
                        "internal transfers).",
                        move.display_name,
                    ))
                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))
                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))
                if counterpart_lines.account_id.account_type == 'asset_receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'
                liquidity_amount = liquidity_lines.amount_currency
                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})
            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    @api.model_create_multi
    def create(self, vals_list):
        if len(vals_list) == 1 and vals_list[0].get('journal_id') and vals_list[0].get('payment_number'):
            account_payments = self.env['account.payment'].search([
                ('journal_id', '=', vals_list[0]['journal_id']),
                ('payment_number', '=', vals_list[0]['payment_number'])
            ])
            if len(account_payments) > 0:
                account_journal = self.env['account.journal'].search([('id', '=', vals_list[0]['journal_id'])])
                raise UserError(
                    f'Ya existe un pago con el diario {account_journal.name} y con el número '
                    f'{vals_list[0]["payment_number"]} creado.'
                )
        return super(AccountPayment, self).create(vals_list)

    def write(self, vals):
        if vals.get('journal_id') or vals.get('payment_number'):
            should_search_journal = False
            if vals.get('journal_id'):
                should_search_journal = True
                journal_id = vals['journal_id']
            else:
                journal_id = self.journal_id.id
                journal = self.journal_id
            payment_number = vals['payment_number'] if vals.get('payment_number') else self.payment_number
            account_payments = self.env['account.payment'].search([
                ('journal_id', '=', journal_id),
                ('payment_number', '=', payment_number)
            ])
            if len(account_payments) > 0:
                if should_search_journal:
                    journal = self.env['account.journal'].search([('id', '=', journal_id)])
                raise UserError(
                    f'Ya existe un pago con el diario {journal.name} y con el número {payment_number} creado.'
                )
        return super(AccountPayment, self).write(vals)


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_number = fields.Char('Número', default='000')
    currency_id = fields.Many2one('res.currency', required=False, default=lambda self: self.env.company.currency_id)
    invoice_origin = fields.Char(
        string='Doc. Fuente',
        stored="True",
        readonly=False,
        tracking=True,
        help="The document(s) that generated the invoice.",
    )
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
        sri_payment = self.env['l10n_ec.sri.payment'].search(
            [('name', '=', 'Otros con utilización del sistema financiero')],
            limit=1
        )
        return sri_payment.id or False

    def _get_accounting_date(self, invoice_date, has_tax):
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        today = fields.Date.context_today(self)
        if not lock_dates:
            return invoice_date
        highest_name = self.highest_name or self._get_last_sequence(relaxed=True, lock=False)
        number_reset = self._deduce_sequence_number_reset(highest_name)
        invoice_date = lock_dates[-1][0] + timedelta(days=1)
        if self.is_sale_document(include_receipts=True):
            if not highest_name or number_reset == 'month':
                return min(today, date_utils.get_month(invoice_date)[1])
            elif number_reset == 'year':
                return min(today, date_utils.end_of(invoice_date, 'year'))
        else:
            if not highest_name or number_reset == 'month':
                if (today.year, today.month) > (invoice_date.year, invoice_date.month):
                    return date_utils.get_month(invoice_date)[1]
                else:
                    return max(invoice_date, today)
            elif number_reset == 'year':
                if today.year > invoice_date.year:
                    return date(invoice_date.year, 12, 31)
                else:
                    return max(invoice_date, today)
        return invoice_date
