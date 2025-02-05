from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from functools import partial
import logging
from contextlib import contextmanager

from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    is_html_empty,
    sql
)

_logger = logging.getLogger(__name__)

class AccountEdiFormat(models.Model):

    _inherit = 'account.edi.format'

    def _l10n_ec_get_xml_common_values(self, move):
        internal_type = move.l10n_latam_document_type_id.internal_type
        return {
            'move': move,
            'sequential': move.name.split('-')[2].rjust(9, '0'),
            'company': move.company_id,
            'journal': move.journal_id,
            'partner': move.commercial_partner_id,
            'partner_sri_code': move.partner_id._get_sri_code_for_partner().value,
            'is_cnote': internal_type == 'credit_note',
            'is_dnote': internal_type == 'debit_note',
            'is_liquidation': internal_type == 'purchase_liquidation',
            'is_invoice': internal_type == 'invoice',
            'is_withhold': move.journal_id.l10n_ec_withhold_type == 'in_withhold',
            'format_num_2': self._l10n_ec_format_number,
            'format_num_6': partial(self._l10n_ec_format_number, decimals=2),
            'currency_round': move.company_currency_id.round,
            'clean_str': self._l10n_ec_remove_newlines,
            'strftime': partial(datetime.strftime, format='%d/%m/%Y'),
        }

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_unbalanced_moves(self, container):
        moves = container['records'].filtered(lambda move: move.line_ids)
        if not moves:
            return []

        self.env['account.move.line'].flush_model(['debit', 'credit', 'balance', 'currency_id', 'move_id'])
        self._cr.execute('''
            SELECT line.move_id,
                   ROUND(SUM(line.debit), currency.decimal_places) AS debit,
                   ROUND(SUM(line.credit), currency.decimal_places) AS credit
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN res_company company ON company.id = move.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.balance), currency.decimal_places) != 0
        ''', [tuple(moves.ids)])
        results = self._cr.fetchall()
        _logger.info(f"🔍 UNBALANCED MOVES: {results}")
        return self._cr.fetchall()  # Devuelve (move_id, sum_debit, sum_credit)

    @contextmanager
    def _check_balanced(self, container):
        ''' Verifica si el asiento contable está balanceado (débito = crédito).
        Si hay una diferencia pequeña, la corrige automáticamente antes de lanzar un error.
        '''
        if self.env.context.get('bypass_check_balance', False):
            yield  # Evita la validación si ya se hizo una corrección
            return

        with self._disable_recursion(container, 'check_move_validity', default=True, target=False) as disabled:
            yield
            if disabled:
                return

        # Obtener movimientos desbalanceados
        unbalanced_moves = self._get_unbalanced_moves(container)

        # Si hay diferencias, intenta corregir antes de lanzar el error
        if unbalanced_moves:
            # 🛠 Corregir formato para _apply_balance_correction
            corrections = [(move_id, sum_debit - sum_credit) for move_id, sum_debit, sum_credit in unbalanced_moves]

            self._apply_balance_correction(corrections)

            # **Evitar recursión** agregando un contexto
            self = self.with_context(bypass_check_balance=True)
            unbalanced_moves = self._get_unbalanced_moves(container)

            if unbalanced_moves:
                error_msg = _("An error has occurred.")
                for move_id, sum_debit, sum_credit, balance in unbalanced_moves:
                    move = self.browse(move_id)
                    error_msg += _(
                        "\n\n"
                        "The move (%s) is not balanced.\n"
                        "Total debits: %s\n"
                        "Total credits: %s\n"
                        "You might want to specify a default account on journal \"%s\" to automatically balance each move.",
                        move.display_name,
                        format_amount(self.env, sum_debit, move.company_id.currency_id),
                        format_amount(self.env, sum_credit, move.company_id.currency_id),
                        move.journal_id.name
                    )
                raise UserError(error_msg)

    def _apply_balance_correction(self, corrections):
        """ Ajusta automáticamente el crédito o débito en los movimientos con desbalance """
        for move_id, sum_debit, sum_credit, balance in corrections:
            move = self.browse(move_id)

            if balance > 0:  # Falta crédito
                last_debit_line = move.line_ids.filtered(lambda line: line.debit > 0)
                if last_debit_line:
                    last_debit_line = last_debit_line[-1]
                    last_debit_line.with_context(bypass_check_balance=True).write(
                        {'debit': last_debit_line.debit + balance})

            elif balance < 0:  # Falta débito
                last_credit_line = move.line_ids.filtered(lambda line: line.credit > 0)
                if last_credit_line:
                    last_credit_line = last_credit_line[-1]
                    last_credit_line.with_context(bypass_check_balance=True).write(
                        {'credit': last_credit_line.credit - balance})
