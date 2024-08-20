from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import models, fields, api, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('pending', "Presupuesto"),
            ('sent', "Quotation Sent"),
            ('accredited', "Accredited"),
            ('accredited_confirm', "Accredited Confirm"),
            ('sale', "Sales Order"),
            ('done', "Locked"),
            ('cancel', "Cancelled"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')

    payment_option = fields.Selection(
        selection=[
            ('transfer', "Transferencia / Deposito"),
            ('payment_agreement', "Acuerdo de pago"),
            ('cash', "Efectivo"),
        ],
        string="Payment Option",
    )
    observation = fields.Char(string="Observaciones", readonly=False, tracking=True)

    all_pickings_done = fields.Boolean("All Pickings Done", compute='_compute_all_pickings_done')
    # has_invoices = fields.Boolean("Has Invoices", compute='_compute_has_invoices')
    # ready_for_invoice = fields.Boolean("Ready for Invoice", compute='_compute_ready_for_invoice')

    is_pichincha_user = fields.Boolean(string="Is Pichincha User", store=True, readonly=False)


    def action_view_delivery(self):
        current_user = self.env.user
        # Accedemos directamente a la ubicación de facturación del usuario logueado
        user_billing_location = current_user.billing_location
        if user_billing_location and user_billing_location.state_id.name == 'Pichincha':
            return self._get_action_view_picking(self.picking_ids)
        else:
            raise ValidationError("Solo usuarios de Quito pueden acceder a ordenes de producción")

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_all_pickings_done(self):
        for order in self:
            order.all_pickings_done = all(picking.state == 'done' for picking in order.picking_ids)

    # @api.depends('invoice_ids')
    # def _compute_has_invoices(self):
    #     for order in self:
    #         order.has_invoices = bool(order.invoice_ids)
    #
    # @api.depends('all_pickings_done', 'has_invoices')
    # def _compute_ready_for_invoice(self):
    #     for order in self:
    #         order.ready_for_invoice = order.all_pickings_done and order.has_invoices

    def action_open_payment_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registrar Abono',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('l16n_ec_doopler_activities.view_sale_order_payment_form').id,
            'target': 'new',
            'res_id': self.id,
        }

    def action_apply_payment(self):
        if not self.payment_option:
            raise ValidationError("Por favor seleccione un método de pago.")

        # Cambiar el estado a 'accredited'
        self.state = 'accredited'

        # Registrar el evento en el historial
        message = f"Abonado por {dict(self._fields['payment_option'].selection).get(self.payment_option)} el {fields.Datetime.to_string(fields.Datetime.now())} por {self.env.user.name}"
        self.message_post(body=message)

    def action_confirm_accredited(self):
        # Cambiar el estado a 'accredited'
        self.state = 'accredited_confirm'

        # Registrar el evento en el historial
        message = f"Abonado confirmado el {fields.Datetime.to_string(fields.Datetime.now())} por {self.env.user.name}"
        self.message_post(body=message)

    def _prepare_confirmation_values(self):
        """ Prepare the sales order confirmation values.

        Note: self can contain multiple records.

        :return: Sales Order confirmation values
        :rtype: dict
        """
        return {
            'state': 'sale',
            'date_order': fields.Datetime.now()
        }

    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm locked or cancelled SO's
        """
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                "It is not allowed to confirm an order in the following states: %s",
                ", ".join(self._get_forbidden_state_confirm()),
            ))

        self.order_line._validate_analytic_distribution()

        for order in self:
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()

        if self[:1].create_uid.has_group('sale.group_auto_done_setting'):
            # Public user can confirm SO, so we check the group on any record creator.
            self.action_done()

        self.write({'state': 'pending'})

        return True


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoices(self, sale_orders):
        sale_orders.state = 'sale'
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            return sale_orders._create_invoices(final=self.deduct_down_payments)
        else:
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids

            # Create deposit product if necessary
            if not self.product_id:
                self.product_id = self.env['product.product'].create(
                    self._prepare_down_payment_product_values()
                )
                self.env['ir.config_parameter'].sudo().set_param(
                    'sale.default_deposit_product_id', self.product_id.id)

            # Create down payment section if necessary
            if not any(line.display_type and line.is_downpayment for line in order.order_line):
                self.env['sale.order.line'].create(
                    self._prepare_down_payment_section_values(order)
                )

            down_payment_so_line = self.env['sale.order.line'].create(
                self._prepare_so_line_values(order)
            )

            invoice = self.env['account.move'].sudo().create(
                self._prepare_invoice_values(order, down_payment_so_line)
            ).with_user(self.env.uid)  # Unsudo the invoice after creation

            invoice.message_post_with_view(
                'mail.message_origin_link',
                values={'self': invoice, 'origin': order},
                subtype_id=self.env.ref('mail.mt_note').id)

            return invoice

    def create_invoices(self):
        self._create_invoices(self.sale_order_ids)

        if self.env.context.get('open_invoices'):
            return self.sale_order_ids.action_view_invoice()

        #self.sale_order_ids.state = 'accredited_confirm'

        return {'type': 'ir.actions.act_window_close'}

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_unit = fields.Float(
        string='Unit Price',
        compute="_compute_price_unit",
        store=True,
        readonly=False,
        precompute=True,
        digits=(16, 3)
    )

    @api.onchange('product_id')
    def _onchange_product_id_update_account(self):
        if not self.product_id or not self.move_id:
            return

        # Obtener la cuenta contable del producto
        fiscal_position = self.move_id.fiscal_position_id
        accounts = self.with_company(self.company_id).product_id \
            .product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)

        if self.move_id.is_sale_document(include_receipts=True):
            self.account_id = accounts['income'] or self.account_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            self.account_id = accounts['expense'] or self.account_id

        if self.move_id.l10n_ec_authorization_number:
            self.account_id = accounts['expense']

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        for line in self:
            if not line.move_id.l10n_ec_authorization_number:
                if not line.product_id or line.display_type in ('line_section', 'line_note'):
                    continue
                if line.move_id.is_sale_document(include_receipts=True):
                    document_type = 'sale'
                elif line.move_id.is_purchase_document(include_receipts=True):
                    document_type = 'purchase'
                else:
                    document_type = 'other'
                line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.move_id.company_id,
                    line.move_id.currency_id,
                    line.move_id.date,
                    document_type,
                    fiscal_position=line.move_id.fiscal_position_id,
                    product_uom=line.product_uom_id,
                )



