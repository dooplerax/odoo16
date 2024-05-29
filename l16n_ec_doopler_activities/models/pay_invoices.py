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

    invoice_lines = fields.One2many('account.move.invoice.line', 'move_id', string='Invoice Lines')

class AccountPayment(models.Model):
    _inherit = "account.payment"

    invoice_ids = fields.Many2many('account.move', string='Facturas')

    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=False)

    move_ids = fields.One2many('account.move', 'payment_id', string="Moves")

    move_name = fields.Char(related='move_id.name', string="Journal Entry Name", readonly=True)
    move_invoice_partner_display_name = fields.Char(related='move_id.invoice_partner_display_name', string="Vendor/Customer", readonly=True)
    move_invoice_date = fields.Date(related='move_id.invoice_date', string="Invoice/Bill Date", readonly=True)
    move_date = fields.Date(related='move_id.date', string="Accounting Date", readonly=True)
    move_invoice_date_due = fields.Date(related='move_id.invoice_date_due', string="Due Date", readonly=True)
    move_invoice_origin = fields.Char(related='move_id.invoice_origin', string="Source Document", readonly=True)
    move_payment_reference = fields.Char(related='move_id.payment_reference', string="Payment Reference", readonly=True)
    move_ref = fields.Char(related='move_id.ref', string="Reference", readonly=True)
    move_invoice_user_id = fields.Many2one(related='move_id.invoice_user_id', string="Salesperson", readonly=True)
    move_activity_ids = fields.One2many(related='move_id.activity_ids', string="Activities", readonly=True)
    move_company_id = fields.Many2one(related='move_id.company_id', string="Company", readonly=True)
    move_amount_untaxed_signed = fields.Monetary(related='move_id.amount_untaxed_signed', string="Tax Excluded", readonly=True)
    move_amount_tax_signed = fields.Monetary(related='move_id.amount_tax_signed', string="Tax", readonly=True)
    move_amount_total_signed = fields.Monetary(related='move_id.amount_total_signed', string="Total", readonly=True)
    move_amount_total_in_currency_signed = fields.Monetary(related='move_id.amount_total_in_currency_signed', string="Total in Currency", readonly=True)
    move_amount_residual_signed = fields.Monetary(related='move_id.amount_residual_signed', string="Amount Due", readonly=True)
    move_currency_id = fields.Many2one(related='move_id.currency_id', string="Currency", readonly=True)
    move_company_currency_id = fields.Many2one(related='move_id.company_currency_id', string="Company Currency", readonly=True)
    move_to_check = fields.Boolean(related='move_id.to_check', string="To Check", readonly=True)
    move_payment_state = fields.Selection(related='move_id.payment_state', string="Payment State", readonly=True)
    move_state = fields.Selection(related='move_id.state', string="State", readonly=True)
    move_move_type = fields.Selection(related='move_id.move_type', string="Move Type", readonly=True)
    move_pagos = fields.Boolean(related='move_id.pagos', string="Pagos", readonly=False)
    move_residual = fields.Monetary(related='move_id.amount_residual', readonly=True, string="Saldo")

    @api.depends('amount_residual')
    def _compute_residual(self):
        for invoice in self:
            invoice.residual = invoice.amount_residual

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

            self.invoice_ids = [(6, 0, invoices.ids)]
        else:
            self.invoice_ids = [(5,)]

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

            # Crear el asiento contable antes de pagar las facturas
            move_vals = {
                'move_type': 'entry',
                'date': fields.Date.context_today(self),
                'journal_id': self.journal_id.id,
                'line_ids': []
            }

            # Primera línea: total pagado en la cuenta bancaria
            move_vals['line_ids'].append((0, 0, {
                'name': 'Pago de facturas múltiples',
                'account_id': self.journal_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'debit': remaining_amount,
                'credit': 0.0,
            }))

            total_debit = remaining_amount
            total_credit = 0.0

            # Añadir las líneas de las facturas y asignar pagos
            for invoice in invoices_to_pay:
                if remaining_amount <= 0:
                    break

                account_id = invoice.partner_id.property_account_receivable_id.id if invoice.move_type == 'out_invoice' else invoice.partner_id.property_account_payable_id.id
                invoice_amount = min(invoice.amount_residual, remaining_amount)

                move_vals['line_ids'].append((0, 0, {
                    'name': invoice.name,
                    'account_id': account_id,
                    'partner_id': invoice.partner_id.id,
                    'debit': 0.0 if invoice.move_type == 'out_invoice' else invoice_amount,
                    'credit': invoice_amount if invoice.move_type == 'out_invoice' else 0.0,
                }))

                remaining_amount -= invoice_amount
                total_debit += 0.0 if invoice.move_type == 'out_invoice' else invoice_amount
                total_credit += invoice_amount if invoice.move_type == 'out_invoice' else 0.0

                # Asignar líneas pendientes a las facturas pagadas
                move_lines = self.move_id.line_ids.filtered(
                    lambda record: record.account_type in (
                        'asset_receivable', 'liability_payable') and not record.reconciled
                )
                for line in move_lines:
                    invoice.js_assign_outstanding_line(line.id)

                # Marcar las facturas como pagadas o parcialmente pagadas
                invoice.payment_state = 'paid' if invoice.amount_residual == 0 else 'partial'

            # Ajustar el asiento contable si es necesario
            if total_debit != total_credit:
                if total_debit > total_credit:
                    move_vals['line_ids'].append((0, 0, {
                        'name': 'Ajuste para balancear el asiento',
                        'account_id': self.journal_id.default_account_id.id,
                        'partner_id': self.partner_id.id,
                        'debit': 0.0,
                        'credit': total_debit - total_credit,
                    }))
                else:
                    move_vals['line_ids'].append((0, 0, {
                        'name': 'Ajuste para balancear el asiento',
                        'account_id': self.journal_id.default_account_id.id,
                        'partner_id': self.partner_id.id,
                        'debit': total_credit - total_debit,
                        'credit': 0.0,
                    }))

            # Crear el movimiento contable
            move = self.env['account.move'].create(move_vals)

            # Recuperar las líneas de factura asociadas al asiento contable vinculado al pago
            existing_lines = self.env['account.move.invoice.line'].search([('move_id', '=', self.move_id.id)])
            print("Existing Lines: %s", existing_lines)

            # Verificar si existen líneas para eliminar
            if existing_lines:
                # Eliminar las líneas existentes
                existing_lines.unlink()

            # Agregar los datos de las facturas pagadas al modelo AccountMoveInvoiceLine
            new_invoice_lines = []
            label_text_cli = f"Pago de cliente ${self.amount:.2f} - {self.partner_id.name} - {self.move_id.date}"
            label_text_prov = f"Pago de Proveedor ${self.amount:.2f} - {self.partner_id.name} - {self.move_id.date}"
            additional_line = {
                'move_id': self.move_id.id,
                'account_id': self.journal_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'label': label_text_cli if invoice.move_type == 'out_invoice' else label_text_prov,
                'debit': self.amount if invoice.move_type == 'out_invoice' else 0.0,
                'credit': 0.0 if invoice.move_type == 'out_invoice' else self.amount,
            }

            # Añadir la línea adicional al principio de la lista
            new_invoice_lines.append(additional_line)
            for invoice in invoices_to_pay:
                account_id = invoice.partner_id.property_account_receivable_id.id if invoice.move_type == 'out_invoice' else invoice.partner_id.property_account_payable_id.id
                invoice_amount = invoice.amount_residual if invoice.amount_residual != 0 else invoice.amount_total
                new_invoice_lines.append({
                    'move_id': self.move_id.id,  # Aquí se usa el ID del asiento contable actual
                    'account_id': account_id,
                    'partner_id': invoice.partner_id.id,
                    'label': invoice.name,
                    'debit': 0.0 if invoice.move_type == 'out_invoice' else invoice_amount,
                    'credit': invoice_amount if invoice.move_type == 'out_invoice' else 0.0,
                })

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
                    'label': 'Saldo diferencial de Asiento Contable',
                    'debit': adjustment_amount if total_debit < total_credit else 0.0,
                    'credit': adjustment_amount if total_debit > total_credit else 0.0,
                }
                new_invoice_lines.append(adjustment_line)

            # Crear las líneas de factura en el modelo AccountMoveInvoiceLine
            self.env['account.move.invoice.line'].create(new_invoice_lines)

            # Publicar el movimiento contable
            move.action_post()



    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
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

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))

                # if len(counterpart_lines) != 1:
                #     raise UserError(_(
                #         "Journal Entry %s is not valid. In order to proceed, the journal items must "
                #         "include one and only one receivable/payable account (with an exception of "
                #         "internal transfers).",
                #         move.display_name,
                #     ))

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

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            write_off_line_vals = []
            if liquidity_lines and counterpart_lines and writeoff_lines:
                write_off_line_vals.append({
                    'name': writeoff_lines[0].name,
                    'account_id': writeoff_lines[0].account_id.id,
                    'partner_id': writeoff_lines[0].partner_id.id,
                    'currency_id': writeoff_lines[0].currency_id.id,
                    'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
                    'balance': sum(writeoff_lines.mapped('balance')),
                })

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines[0].id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
            ]

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id\
                .with_context(skip_invoice_sync=True)\
                .write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })


