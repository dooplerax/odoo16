from odoo import fields, models, api, _, Command
from collections import defaultdict


class L10nEcWizardAccountWithhold(models.TransientModel):
    _inherit = 'l10n_ec.wizard.account.withhold'

    def _prepare_withhold_header(self):
        res = super()._prepare_withhold_header()
        doc_type = self.env['l10n_latam.document.type'].search([("code", "=", "07")], limit=1)
        res['l10n_latam_document_type_id'] = doc_type.id if doc_type else False
        return res

    def _prepare_withhold_move_lines(self):
        total_per_invoice = defaultdict(lambda: [0, self.env['l10n_ec.wizard.account.withhold.line']])
        total_lines = []

        # 1. Create the base line (and its counterpart to cancel out) for every withhold line.  Tax lines will be created automatically.
        for line in self.withhold_line_ids:
            dummy, account = line._tax_compute_all_helper(1.0, line.tax_id)
            total_per_invoice[line.invoice_id][0] += line.amount
            total_per_invoice[line.invoice_id][1] = line

            nice_base_label_elements = []
            if line.tax_id.l10n_ec_code_base:
                nice_base_label_elements.append(line.tax_id.l10n_ec_code_base)
            nice_base_label_elements.append("{:.2f}%".format(abs(line.tax_id.amount)))
            nice_base_label_elements.append(line.invoice_id.name)
            nice_base_label = ", ".join(nice_base_label_elements)
            vals_base_line = {
                **self._get_move_line_default_values(line, line.base, 'in_withhold'),
                'name': 'Base Ret: ' + nice_base_label,
                'tax_ids': [Command.set(line.tax_id.ids)],
                'account_id': account,
            }
            total_lines.append(vals_base_line)

            vals_base_line_counterpart = {
                **self._get_move_line_default_values(line, line.base, 'out_withhold'),  # Counterpart 0 operation
                'name': 'Base Ret Cont: ' + nice_base_label,
                'account_id': account,
            }
            total_lines.append(vals_base_line_counterpart)

        # 2. Payable/Receivable line
        # One line for each invoice linked with it
        for invoice, (amount, line) in total_per_invoice.items():
            if self.currency_id.compare_amounts(amount, 0) > 0:
                account = self._get_partner_account(self.partner_id, self.withhold_type)
                vals = {
                    **self._get_move_line_default_values(line, amount, 'out_withhold'),
                    'name': _('Withhold on: %s') % invoice.name,
                    'account_id': account.id,
                }
                total_lines.append(vals)
        return total_lines

    @api.model
    def _get_move_line_default_values(self, line, price, debit_wh_type):
        return {
            'partner_id': self.partner_id.commercial_partner_id.id,
            'quantity': 1.0,
            'price_unit': price,
            'debit': price if self.withhold_type != debit_wh_type else 0.0,
            'credit': price if self.withhold_type == debit_wh_type else 0.0,
            'tax_base_amount': 0.0,
            'display_type': 'product',
            'l10n_ec_withhold_invoice_id': line.invoice_id.id,
            'l10n_ec_code_taxsupport': line.taxsupport_code,
        }
