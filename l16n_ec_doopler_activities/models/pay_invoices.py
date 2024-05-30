from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import models, fields, api, _, Command



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * exchange_partials:    A recorset of all account.partial.reconcile created during the reconciliation
                                        with the exchange difference journal entries.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {'exchange_partials': self.env['account.partial.reconcile']}

        if not self:
            return results

        not_paid_invoices = self.move_id.filtered(lambda move:
                                                  move.is_invoice(include_receipts=True)
                                                  and move.payment_state not in ('paid', 'in_payment')
                                                  )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.account_type not in (
            'asset_cash', 'liability_credit_card'):
                raise UserError(
                    _("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                    % line.account_id.display_name)
            if line.move_id.state not in ('posted', 'draft'):
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        if self._context.get('reduced_line_sorting'):
            sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id)
        else:
            sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency)
        sorted_lines = self.sorted(key=sorting_f)

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines._all_reconciled_lines()
        involved_partials = involved_lines.matched_credit_ids | involved_lines.matched_debit_ids

        # ==== Create partials ====

        partial_no_exch_diff = bool(
            self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
        sorted_lines_ctx = sorted_lines.with_context(
            no_exchange_difference=self._context.get('no_exchange_difference') or partial_no_exch_diff)
        partials = sorted_lines_ctx._create_reconciliation_partials()
        results['partials'] = partials
        involved_partials += partials
        exchange_move_lines = partials.exchange_move_id.line_ids.filtered(lambda line: line.account_id == account)
        involved_lines += exchange_move_lines
        exchange_diff_partials = exchange_move_lines.matched_debit_ids + exchange_move_lines.matched_credit_ids
        involved_partials += exchange_diff_partials
        results['exchange_partials'] += exchange_diff_partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.company_id.tax_exigibility and account.account_type in (
        'asset_receivable', 'liability_payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel') and not self._context.get(
                'no_cash_basis'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

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

    amount_pay = fields.Monetary(string="A pagar", compute='_compute_amount_pay', store=True, copy=False)

    saldo = fields.Monetary(string="Saldo", compute='_compute_saldo', store=True, copy=False)

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

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for payment in self:
            payment.invoice_count = len(payment.invoice_ids)

    @api.depends('invoice_ids')
    def _compute_paid_invoices_count(self):
        for payment in self:
            paid_invoices = payment.invoice_ids.filtered(lambda inv: inv.payment_state in ['paid', 'partial'])
            payment.paid_invoices_count = len(paid_invoices)


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

    def action_open_invoices(self):
        self.ensure_one()
        # Obteniendo las IDs de las facturas asociadas al pago
        invoice_ids = self.invoice_ids.ids

        # Retornando la acción para abrir la vista de las facturas
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facturas Asociadas',
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

                if invoice.amount_pay <= 0:
                    raise UserError(f"El valor a pagar de la factura {invoice.name} es menor o igual a 0.")

                if invoice.amount_pay > invoice.amount_residual:
                    raise UserError(f"El valor a pagar de la factura {invoice.name} es mayor que el monto restante.")

                account_id = invoice.partner_id.property_account_receivable_id.id if invoice.move_type == 'out_invoice' else invoice.partner_id.property_account_payable_id.id
                invoice_amount = min(invoice.amount_pay, remaining_amount)

                move_vals['line_ids'].append((0, 0, {
                    'name': invoice.name,
                    'account_id': account_id,
                    'partner_id': invoice.partner_id.id,
                    'debit': 0.0 if invoice.move_type == 'out_invoice' else invoice_amount,
                    'credit': invoice_amount if invoice.move_type == 'out_invoice' else 0.0,
                }))

                remaining_amount -= invoice_amount  # Reducir el monto restante a pagar
                total_debit += 0.0 if invoice.move_type == 'out_invoice' else invoice_amount
                total_credit += invoice_amount if invoice.move_type == 'out_invoice' else 0.0

                # Marcar las facturas como pagadas o parcialmente pagadas
                invoice.amount_residual -= invoice_amount
                invoice.payment_state = 'paid' if invoice.amount_residual == 0 else 'partial'

                # Crear el registro del pago y reconciliar
                payment = self.env['account.payment'].create({
                    'payment_type': 'inbound' if invoice.move_type == 'out_invoice' else 'outbound',
                    'partner_type': 'customer' if invoice.move_type == 'out_invoice' else 'supplier',
                    'partner_id': invoice.partner_id.id,
                    'amount': invoice_amount,
                    'journal_id': self.journal_id.id,
                    'payment_method_id': self.env.ref(
                        'account.account_payment_method_manual_in').id if invoice.move_type == 'out_invoice' else self.env.ref(
                        'account.account_payment_method_manual_out').id,
                    'invoice_ids': [(6, 0, [invoice.id])],
                })

                # Reconciliar el pago con la factura
                for line in (invoice.line_ids + payment.move_id.line_ids).filtered(
                        lambda record: record.account_type in ('asset_receivable', 'liability_payable') and not record.reconciled):
                    line.reconcile()

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
                'debit': invoice_amount if invoice.move_type == 'out_invoice' else 0.0,
                'credit': 0.0 if invoice.move_type == 'out_invoice' else invoice_amount,
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

            for invoice in invoices_to_pay:
                print(f"Valor residual de la factura {invoice.name}: {invoice.amount_residual}")

            invoices_to_pay.write({'pagos': False})
            invoices_to_pay.write({'amount_pay': invoice.amount_residual})


