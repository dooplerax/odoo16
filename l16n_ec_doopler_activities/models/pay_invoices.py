from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import models, fields, api, _, Command

class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)

class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    payment_method_id = fields.Many2one(
        string='Payment Method',
        comodel_name='account.payment.method',
        domain=False,
        required=True,
        ondelete='cascade'
    )

class AccountMove(models.Model):
    _inherit = "account.move"

    pagos = fields.Boolean(string="Pagos", readonly=False)

    amount_pay = fields.Monetary(string="A pagar", compute="_compute_amount_pay", store=True, copy=False)

    saldo = fields.Monetary(string="Saldo", compute="_compute_saldo", store=True, copy=False)

    invoice_lines = fields.One2many('account.move.invoice.line', 'move_id', string='Invoice Lines', copy=False)

    @api.depends('amount_residual')
    def _compute_saldo(self):
        for move in self:
            move.saldo = sum(move.mapped('amount_residual'))

    @api.depends('amount_residual')
    def _compute_amount_pay(self):
        for move in self:
            move.amount_pay = sum(move.mapped('amount_residual'))
            print("Valor residual de la factura", move.amount_pay)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    invoice_ids = fields.Many2many('account.move', string='Facturas', copy=False)

    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=False, copy=False)

    move_ids = fields.One2many('account.move', 'payment_id', string="Moves", copy=False)

    move_name = fields.Char(related='move_id.name', string="Journal Entry Name", readonly=True, copy=False)
    move_invoice_partner_display_name = fields.Char(related='move_id.invoice_partner_display_name', string="Vendor/Customer", readonly=True, copy=False)
    move_invoice_date = fields.Date(related='move_id.invoice_date', string="Invoice/Bill Date", readonly=True, copy=False)
    move_date = fields.Date(related='move_id.date', string="Accounting Date", readonly=True, copy=False)
    move_invoice_date_due = fields.Date(related='move_id.invoice_date_due', string="Due Date", readonly=True, copy=False)
    move_invoice_origin = fields.Char(related='move_id.invoice_origin', string="Source Document", readonly=False, copy=False)
    move_payment_reference = fields.Char(related='move_id.payment_reference', string="Payment Reference", readonly=True, copy=False)
    move_ref = fields.Char(related='move_id.ref', string="Reference", readonly=True, copy=False)
    move_invoice_user_id = fields.Many2one(related='move_id.invoice_user_id', string="Salesperson", readonly=True, copy=False)
    move_activity_ids = fields.One2many(related='move_id.activity_ids', string="Activities", readonly=True, copy=False)
    move_company_id = fields.Many2one(related='move_id.company_id', string="Company", readonly=True, copy=False)
    move_amount_untaxed_signed = fields.Monetary(related='move_id.amount_untaxed_signed', string="Tax Excluded", readonly=True, copy=False)
    move_amount_tax_signed = fields.Monetary(related='move_id.amount_tax_signed', string="Tax", readonly=True, copy=False)
    move_amount_total_signed = fields.Monetary(related='move_id.amount_total_signed', string="Total", readonly=True, copy=False)
    move_amount_total_in_currency_signed = fields.Monetary(related='move_id.amount_total_in_currency_signed', string="Total in Currency", readonly=True, copy=False)
    move_amount_residual_signed = fields.Monetary(related='move_id.amount_residual_signed', string="Amount Due", readonly=True, copy=False)
    move_currency_id = fields.Many2one(related='move_id.currency_id', string="Currency", readonly=True, copy=False)
    move_company_currency_id = fields.Many2one(related='move_id.company_currency_id', string="Company Currency", readonly=True, copy=False)
    move_to_check = fields.Boolean(related='move_id.to_check', string="To Check", readonly=True, copy=False)
    move_payment_state = fields.Selection(related='move_id.payment_state', string="Payment State", readonly=True, copy=False)
    move_state = fields.Selection(related='move_id.state', string="State", readonly=True, copy=False)
    move_move_type = fields.Selection(related='move_id.move_type', string="Move Type", readonly=True, copy=False)
    move_pagos = fields.Boolean(related='move_id.pagos', string="Pagos", readonly=False, copy=False)
    move_residual = fields.Monetary(related='move_id.saldo', readonly=True, string="Saldo", copy=False)
    residual = fields.Monetary(related='move_id.amount_pay', readonly=False, string="A pagar", copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    paid_invoices_count = fields.Integer(string='Paid Invoices Count', compute='_compute_paid_invoices_count')
    saldo_favor = fields.Monetary(readonly=True, string="Saldo a favor", copy=False)
    mark_payment_checkbox = fields.Boolean(string="Seleccionar todas las facturas")
    # amount = fields.Monetary(currency_field='currency_id', compute='_compute_total_amount_pay')
    #
    # @api.depends('invoice_ids')
    # def _compute_total_amount_pay(self):
    #     self.amount = sum(self.invoice_ids.mapped('amount_pay'))

    @api.onchange('mark_payment_checkbox')
    def _onchange_mark_payment_checkbox(self):
        if self.mark_payment_checkbox:
            self.invoice_ids.write({'pagos': True})
        else:
            self.invoice_ids.write({'pagos': False})

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for payment in self:
            payment.invoice_count = len(payment.invoice_ids)

    @api.depends('invoice_ids', 'move_ids.line_ids.move_id')
    def _compute_paid_invoices_count(self):
        for payment in self:
            # Obtener las facturas relacionadas directamente con el pago y aquellas enlazadas mediante move_ids
            related_invoices = payment.invoice_ids | payment.move_ids.mapped('line_ids.move_id')
            # Filtrar las facturas que están pagadas o parcialmente pagadas y que fueron pagadas con este pago
            paid_invoices = related_invoices.filtered(
                lambda inv: inv.payment_state in ['paid', 'partial'] and payment in inv.payment_ids)
            payment.paid_invoices_count = len(paid_invoices)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            payment_type = self.env.context.get('default_payment_type')
            if payment_type == 'outbound':
                # Facturas de proveedores para pagos salientes
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'in_invoice')  # Solo facturas de proveedores
                ])
            elif payment_type == 'inbound':
                # Facturas de clientes para pagos entrantes
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')  # Solo facturas de clientes
                ])
            else:
                invoices = self.env['account.move']

            if not invoices:
                raise UserError("No hay facturas pendientes para %s." % self.partner_id.name)

            self.invoice_ids = [(6, 0, invoices.ids)]
        else:
            self.invoice_ids = [(5,)]

    def action_open_invoices(self):
        self.ensure_one()
        # Obteniendo las IDs de las facturas asociadas al pago
        invoice_ids = self.invoice_ids.ids

        # Retornando la acción para abrir la vista de las facturas
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalles',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoice_ids)],
            'context': dict(self._context),
        }

    def action_post(self):
        # Llamar al método original
        super(AccountPayment, self).action_post()

        if any(invoice.pagos for invoice in self.invoice_ids) and self.amount <= 0:
            raise UserError("Hay facturas seleccionadas para pagar, pero el valor del importe es menor o igual a 0.")

        # Lógica personalizada para pagar facturas con el check de pagos activo
        invoices_to_pay = self.invoice_ids.filtered(lambda inv: inv.pagos)

        if invoices_to_pay:
            self.payment_cross_invoice(invoices_to_pay)
        return

    def action_draft(self):
        if self.move_id.state == 'posted' and self.move_id.move_type == 'entry':
            raise UserError(_("No se puede cambiar a estado borrador, debido que, este pago esta atado a un asiento publicado"))

        self.move_id.button_draft()

    def payment_cross_invoice(self, invoices_to_pay):
        partner_account = self.partner_id.property_account_receivable_id.id if self.payment_type == 'inbound' else self.partner_id.property_account_payable_id.id
        journal_id = self.company_id.journal_cross_payment_id.id
        date = self.move_id.date
        company_id = self.env.company.id
        amount_invoice = sum(invoices_to_pay.mapped('amount_pay'))

        inter_move_vals = {
            'journal_id': journal_id,
            'date': date,
            'company_id': company_id,
            'ref': _('Cruce del pago %s') % self.name,
            'line_ids': [
                (0, 0, {
                    'account_id': partner_account,
                    'debit': amount_invoice if self.payment_type == 'inbound' else 0.0,
                    'credit': 0.0 if self.payment_type == 'inbound' else amount_invoice,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'account_id': self.company_id.account_cross_payment_id.id,
                    'debit': 0.0 if self.payment_type == 'inbound' else amount_invoice,
                    'credit': amount_invoice if self.payment_type == 'inbound' else 0.0,
                    'partner_id': self.partner_id.id,
                }),
            ]
        }
        inter_move = self.env['account.move'].create(inter_move_vals)
        inter_move.action_post()

        orig_line = self.move_id.line_ids.filtered(lambda l: l.account_id.id == partner_account)
        inter_line = inter_move.line_ids.filtered(lambda l: l.account_id.id == partner_account)
        (orig_line + inter_line).reconcile()

        final_lines = [
            (0, 0, {
                'account_id': self.company_id.account_cross_payment_id.id,
                'debit': amount_invoice if self.payment_type == 'inbound' else 0.0,
                'credit': 0.0 if self.payment_type == 'inbound' else amount_invoice,
                'partner_id': self.partner_id.id,
            }),
        ]
        remaining = amount_invoice
        for inv in invoices_to_pay:
            pay_amt = min(remaining, inv.amount_pay)
            remaining -= pay_amt
            final_lines.append((0, 0, {
                'account_id': partner_account,
                'debit': 0.0 if self.payment_type == 'inbound' else pay_amt,
                'credit': pay_amt if self.payment_type == 'inbound' else 0.0,
                'partner_id': inv.partner_id.id,
                'name': _('Pago de factura %s') % inv.name,
            }))
            if remaining <= 0:
                break

        final_move = self.env['account.move'].create({
            'journal_id': journal_id,
            'date': date,
            'company_id': company_id,
            'ref': _('Asiento de distribución del pago %s') % self.name,
            'line_ids': final_lines,
        })
        final_move.action_post()

        inter_line = inter_move.line_ids.filtered(lambda l: l.account_id.id == self.company_id.account_cross_payment_id.id)
        final_line = final_move.line_ids.filtered(lambda l: l.account_id.id == self.company_id.account_cross_payment_id.id)
        (inter_line + final_line).reconcile()

        for inv in invoices_to_pay:
            inv_lines = inv.line_ids.filtered(lambda l: l.account_id.id == partner_account and not l.reconciled)
            pay_lines = final_move.line_ids.filtered(
                lambda l: l.account_id.id == partner_account and l.name == _('Pago de factura %s') % inv.name
            )
            (inv_lines + pay_lines).reconcile()

        return True

class ResCompany(models.Model):
    _inherit = 'res.company'

    journal_cross_payment_id = fields.Many2one(
        'account.journal',
        string="Diario para cruces internos de pagos",
    )
    account_cross_payment_id = fields.Many2one('account.account',
                                               string="Cuenta para cruces internos de pagos",
                                               domain="[('deprecated', '=', False)]",
                                            )

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    journal_cross_payment_id = fields.Many2one('account.journal',
                                               string="Diario para cruces internos de pagos",
                                               related='company_id.journal_cross_payment_id',
                                               readonly=False
                                               )
    account_cross_payment_id = fields.Many2one('account.account',
                                               string='Cuenta para cruces de pagos',
                                               related='company_id.account_cross_payment_id',
                                               readonly=False
                                               )

