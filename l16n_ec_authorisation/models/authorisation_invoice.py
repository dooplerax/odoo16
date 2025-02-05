from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from functools import partial
import logging

_logger = logging.getLogger(__name__)

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

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
