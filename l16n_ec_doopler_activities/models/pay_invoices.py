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
            # Inicializar el monto restante a pagar
            remaining_amount = self.amount
            new_invoice_lines = []
            for invoice in invoices_to_pay:
                if remaining_amount <= 0:
                    break

                if invoice.amount_pay <= 0:
                    raise UserError(f"El valor a pagar de la factura {invoice.name} es menor o igual a 0.")

                if invoice.amount_pay > invoice.amount_residual:
                    raise UserError(f"El valor a pagar de la factura {invoice.name} es mayor que el saldo restante.")

                # Obtener el valor a pagar en la factura
                payment_amount = min(remaining_amount, invoice.amount_pay)

                if payment_amount > 0:
                    # Restar el importe pagado del total disponible
                    remaining_amount -= payment_amount

                    # Agregar los datos de las facturas pagadas al modelo AccountMoveInvoiceLine
                    account_id = invoice.partner_id.property_account_receivable_id.id if invoice.move_type == 'out_invoice' else invoice.partner_id.property_account_payable_id.id
                    label_text = invoice.name

                    new_invoice_lines.append({
                        'move_id': self.move_id.id,  # Aquí se usa el ID del asiento contable actual
                        'account_id': account_id,
                        'partner_id': invoice.partner_id.id,
                        'label': label_text,
                        'debit': 0.0 if invoice.move_type == 'out_invoice' else payment_amount,
                        'credit': payment_amount if invoice.move_type == 'out_invoice' else 0.0,
                    })

            # Agregar la línea adicional
            label_text_cli = f"Pago de cliente ${self.amount:.2f} - {self.partner_id.name} - {self.move_id.date}"
            label_text_prov = f"Pago de Proveedor ${self.amount:.2f} - {self.partner_id.name} - {self.move_id.date}"
            additional_line = {
                'move_id': self.move_id.id,
                'account_id': self.journal_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'label': label_text_cli if self.payment_type == 'inbound' else label_text_prov,
                'debit': self.amount if self.payment_type == 'inbound' else 0.0,
                'credit': 0.0 if self.payment_type == 'inbound' else self.amount,
            }
            new_invoice_lines.insert(0, additional_line)

            # Calcular los totales de débito y crédito
            total_debit = sum(line['debit'] for line in new_invoice_lines)
            total_credit = sum(line['credit'] for line in new_invoice_lines)

            # Verificar si se necesita una línea de ajuste
            if total_debit != total_credit:
                adjustment_amount = abs(total_debit - total_credit)
                adjustment_line = {
                    'move_id': self.move_id.id,
                    'account_id': self.journal_id.default_account_id.id,
                    'partner_id': self.partner_id.id,
                    'label': 'Saldo diferencial',
                    'debit': adjustment_amount if total_debit > total_credit else 0.0,
                    'credit': adjustment_amount if total_debit < total_credit else 0.0,
                }
                new_invoice_lines.append(adjustment_line)

            # Crear las líneas de factura en el modelo AccountMoveInvoiceLine
            self.env['account.move.invoice.line'].create(new_invoice_lines)

            # Volver a inicializar el monto restante a pagar
            remaining_amount = self.amount

            # Realizar los pagos usando account.payment.register
            for invoice in invoices_to_pay:
                if remaining_amount <= 0:
                    break

                payment_amount = min(remaining_amount, invoice.amount_pay)

                if payment_amount > 0:
                    # Crear y registrar el pago usando account.payment.register
                    self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=invoice.ids
                    ).create({
                        'payment_date': invoice.date,
                        'amount': payment_amount,
                    })._create_payments()

                    # Restar el importe pagado del total disponible
                    remaining_amount -= payment_amount
                    self.saldo_favor = remaining_amount

                    # Actualizar el estado de pago de la factura
                    invoice._compute_amount()

                    invoice.write({'pagos': False})

    def action_draft(self):
        if self.move_id.state == 'posted' and self.move_id.move_type == 'entry':
            raise UserError(_("No se puede cambiar a estado borrador, debido que, este pago esta atado a un asiento publicado"))

        self.move_id.button_draft()
