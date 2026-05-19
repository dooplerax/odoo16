from collections import defaultdict

from odoo import models, api, Command, _


class L10nEcWizardAccountWithhold(models.TransientModel):
    _inherit = 'l10n_ec.wizard.account.withhold'

    def _prepare_withhold_header(self):
        res = super()._prepare_withhold_header()
        doc_type = self.env['l10n_latam.document.type'].search([("code", "=", "07")], limit=1)
        res['l10n_latam_document_type_id'] = doc_type.id if doc_type else False
        return res

    def _prepare_withhold_move_lines(self):
        if self._is_out_invoice():
            return super(L10nEcWizardAccountWithhold, self)._prepare_withhold_move_lines()
        total_per_invoice = defaultdict(lambda: [0, self.env['l10n_ec.wizard.account.withhold.line']])
        total_lines = []
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
                **self._get_move_line_default_values(line, line.base, 'out_withhold'),
                'name': 'Base Ret Cont: ' + nice_base_label,
                'account_id': account,
            }
            total_lines.append(vals_base_line_counterpart)
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
        if self._is_out_invoice():
            return super(L10nEcWizardAccountWithhold, self)._get_move_line_default_values(line, price, debit_wh_type)
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

    def _is_out_invoice(self):
        return len(self.related_invoice_ids) == 1 and self.related_invoice_ids.move_type == 'out_invoice'
