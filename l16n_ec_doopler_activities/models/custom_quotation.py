from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import models, fields, api, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
import base64
from odoo.tools import html2plaintext
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    note = fields.Text(
        string="Terms and conditions",
        store=True, readonly=False)

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

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_ir_attachment_rel',
        'sale_order_id',
        'attachment_id',
        string='Adjuntar documento'
    )

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

        # Procesar archivos adjuntos si existen
        if self.attachment_ids:
            for attachment in self.attachment_ids:
                # Crear el enlace HTML al archivo adjunto
                attachment_link = f"<a href='/web/content/{attachment.id}?download=true'>{attachment.name}</a>"
                attachment_message = f"Archivo adjunto: {attachment_link}"

                # Registrar el archivo adjunto en el historial
                self.message_post(
                    body=attachment_message,
                    attachment_ids=[attachment.id]
                )

    def action_confirm_accredited(self):
        # Cambiar el estado a 'accredited'
        self.state = 'accredited_confirm'

        # Registrar el evento en el historial
        message = f"Abonado confirmado el {fields.Datetime.to_string(fields.Datetime.now())} por {self.env.user.name}"
        self.message_post(body=message)

        # Filtrar las líneas de la orden por productos habilitados para producción
        production_lines = self.order_line.filtered(lambda line: line.product_template_id.enable_production_order)

        if production_lines:
            # Inicializar los contadores de cortinas
            en_ct, ze_ct, ro_ct, pa_ct, cla_ct, tsh_ct, di_ct, top_ct, tcp_ct = 0, 0, 0, 0, 0, 0, 0, 0, 0

            # Crear la orden de producción
            production_order = self.env['mrp.production'].create({
                'client': self.partner_id.id,
                'costumer': self.customer,
                'entry_date': self.date_order,
                'delivery_date': self.commitment_date,
                'delivery_address': self.dirEntrega,
                'quotation_note': html2plaintext(self.note) if self.note else '',
                'sale_id': self.id,
            })

            for line in production_lines:
                # Incrementar el contador basado en el tipo de cortina
                if line.courtain_type == 'enrollable':
                    en_ct += 1
                elif line.courtain_type == 'zebra':
                    ze_ct += 1
                elif line.courtain_type == 'romana':
                    ro_ct += 1
                elif line.courtain_type == 'panelada':
                    pa_ct += 1
                elif line.courtain_type == 'claraboya':
                    cla_ct += 1
                elif line.courtain_type == 'triple_shade':
                    tsh_ct += 1
                elif line.courtain_type == 'divergence':
                    di_ct += 1
                elif line.courtain_type == 'tradicional_onda_perfecta':
                    top_ct += 1
                elif line.courtain_type == 'tradicional_con_pliegues':
                    tcp_ct += 1

                # Crear la línea de stock move
                values = {
                    'product_id': line.product_id.id,
                    'command': line.command,
                    'ambience': line.ambience,
                    'courtain_type': line.courtain_type,
                    'material': line.material.id,
                    'broad': line.broad,
                    'high': line.high,
                    'encj': line.encj,
                    'mot': line.mot,
                    'clnt': line.clnt,
                    'quantity': line.product_uom_qty,
                    'raw_material_production_id': production_order.id,
                }
                try:
                    self.env['stock.move'].create(values)
                except Exception as e:
                    _logger.error("Error al crear stock.move: %s", e)

            # Actualizar los valores en la orden de producción
            production_order.write({
                'en_ct': en_ct,
                'ze_ct': ze_ct,
                'ro_ct': ro_ct,
                'pa_ct': pa_ct,
                'cla_ct': cla_ct,
                'tsh_ct': tsh_ct,
                'di_ct': di_ct,
                'top_ct': top_ct,
                'tcp_ct': tcp_ct,
            })
        else:
            message_production = "No se encontraron productos habilitados para órdenes de producción en las líneas de cotización."
            self.message_post(body=message_production)

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

class Currency(models.Model):
    _inherit = "res.currency"

    decimal_places = fields.Integer(compute='_compute_decimal_places', readonly=False, store=True,
                                    help='Decimal places taken into account for operations on amounts in this currency. It is determined by the rounding factor.')


