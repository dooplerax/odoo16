from odoo import models, api


class L10nEcWizardAccountWithhold(models.TransientModel):
    _inherit = 'l10n_ec.wizard.account.withhold'

    def _prepare_withhold_header(self):
        res = super()._prepare_withhold_header()
        doc_type = self.env['l10n_latam.document.type'].search([("code", "=", "07")], limit=1)
        res['l10n_latam_document_type_id'] = doc_type.id if doc_type else False
        return res

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
