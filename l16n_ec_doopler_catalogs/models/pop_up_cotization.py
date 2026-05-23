from odoo import api, fields, models, _
from odoo.exceptions import (UserError)
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tools import float_round


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dirEntrega = fields.Char(string="Direccion de entrega")
    customer = fields.Char(string="Customer ")

    partner_shipping_id = fields.Many2one('res.partner', string="Dirección de Entrega",
                                          domain="[('id', 'child_of', partner_id)]")
    amount_tax = fields.Float(string="Impuestos ($)", store=True, compute='_compute_amounts')

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO with rounded tax."""
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            # Redondear el valor del impuesto a 2 decimales
            order.amount_untaxed = amount_untaxed
            order.amount_tax = float_round(amount_tax, precision_digits=2)
            order.amount_total = order.amount_untaxed + order.amount_tax

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            main_address = self.partner_id

            address = "{} - {} - {} - {} - {}".format(
                main_address.street or '',
                main_address.street2 or '',
                main_address.city or '',
                main_address.state_id.name if main_address.state_id else '',
                # main_address.zip or '',
                main_address.country_id.name if main_address.country_id else ''
            )

            self.dirEntrega = address.strip(' -')
        else:
            self.dirEntrega = ''

    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     if self.partner_id:
    #         shipping_address = self.partner_id.child_ids.filtered(lambda p: p.type == 'delivery')[:1]
    #         if shipping_address:
    #             self.partner_shipping_id = shipping_address.id
    #             self.dirEntrega = shipping_address.contact_address
    #         else:
    #             self.dirEntrega = ''

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    quantity = fields.Float(
        string='Quantity',
        store=True, readonly=False,
        digits=(16, 3),
        help="The optional quantity expressed by this line, eg: number of product sold. "
             "The quantity is not a legal requirement but is very useful for some reports.",
    )

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = "Descripción"
    product_details_ok = fields.Boolean(
        string='Product Details', related='product_template_id.details_ok')
    product_type = fields.Selection(
        string='Product Type', related='product_template_id.detailed_type')
    details_name = fields.Char(string='Descripción')

    ambience = fields.Char(selection='_get_ambience_selection', string="Ambiente")
    # new_ambience = fields.Selection(selection='_get_ambience_selection', string="Ambiente")
    courtain_type = fields.Selection(
        selection='_get_tipo_cortina_options', string="Tipo Cortina")
    material = fields.Many2one(
        "product.template", domain="[('class_inherit.cl_name','=','TELAS')]")
    broad = fields.Float(string="Ancho", default=None, digits=(16, 3))
    high = fields.Float(string="Alto", default=None, digits=(16, 3))

    price_subtotal = fields.Float(
        string="Subtotal ($)",
        compute='_compute_amount',
        store=True, precompute=True,
        digits=(16, 3))

    def _get_command_selection(self):
        return [
            ('no_aplica', 'NO APLICA'),
            ('Izquierda', 'IZQUIERDO'),
            ('Derecha', 'DERECHO'),
            ('Ambos', 'AMBOS'),
            ('Fijo', 'FIJA')
        ]

    def _get_ambience_selection(self):
        return [
            ('sala', 'SALA'),
            ('dormitorio', 'DORMITORIO'),
            ('estudio', 'ESTUDIO'),
            ('comedor', 'COMEDOR'),
            ('cocina', 'COCINA'),
            ('area_social', 'ÁREA SOCIAL'),
            ('oficina', 'OFICINA'),
            ('bbq', 'BBQ')
        ]

    command = fields.Selection(
        selection=_get_command_selection,
        string="Mando"
    )

    # ambiente = fields.Char(string="Ambiente", required=True)
    encj = fields.Boolean(string="ENCJ.", default=False)
    mot = fields.Boolean(string="MOT.", default=False)
    clnt = fields.Boolean(string="CINT.", default=False)

    product_uom_qty = fields.Float(
        string="Quantity",
        compute='calculated_quantity_field',
        digits=(16, 3), default=0.0,
        store=True, readonly=False, required=True, precompute=True)

    qty_to_invoice = fields.Float(
        string="Quantity To Invoice",
        compute='_compute_qty_to_invoice',
        digits=(16, 3),
        store=True)

    @api.model
    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        analytic_account_id = self.order_id.analytic_account_id.id
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        if analytic_account_id and not self.display_type:
            analytic_account_id = str(analytic_account_id)
            if 'analytic_distribution' in res:
                res['analytic_distribution'][analytic_account_id] = res['analytic_distribution'].get(
                    analytic_account_id, 0) + 100
            else:
                res['analytic_distribution'] = {analytic_account_id: 100}
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state')
    def _compute_qty_to_invoice(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.state in ['sale', 'done'] and not line.display_type:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.model
    def _get_tipo_cortina_options(self):
        return [
            ('enrollable', 'Enrollable'),
            ('zebra', 'Zebra'),
            ('romana', 'Romana'),
            ('panelada', 'Panelada'),
            ('claraboya', 'Claraboya'),
            ('triple_shade', 'Triple Shade'),
            ('divergence', 'Divergence'),
            ('tradicional', 'Tradicional'),
            ('horizontal', 'Horizontal'),
            ('vertical', 'Vertical'),
            ('tradicional_onda_perfecta', 'Tradicional onda perfecta'),
            ('tradicional_con_pliegues', 'Tradicional con pliegues'),
            # Nuevas opciones motorizadas con el mismo formato:
            ('enrollable_motorizada', 'Roller motorizada'),
            ('zebra_motorizada', 'Zebra motorizada'),
            ('claraboya_motorizada', 'Claraboya motorizada'),
            ('tradicional_onda_perfecta_motorizada', 'Tradicional onda perfecta motorizada'),
            ('tradicional_con_pliegues_motorizada', 'Tradicional con pliegues motorizada'),
            ('panelada_motorizada', 'Panelada motorizada'),
            ('romana_motorizada', 'Romana motorizada'),
        ]

    @api.depends('broad', 'high')
    @api.onchange('product_id')
    def calculated_quantity_field(self):
        for record in self:
            if (record.broad <= 0.0 or record.high <= 0.0):
                record.product_uom_qty = 1
            else:
                record.product_uom_qty = record.broad * record.high

    def name_get(self):
        result = []
        for cat in self:
            material_name = cat.material.name if cat.material else ""
            name = "Tipo de cortina: {} / Materiales: {} / Ancho: {} / Alto: {} / Mando: {} / Ambiente: {} / ENCJ.: {} / MOT.: {} /  CLNT.: {}".format(
                cat.courtain_type,
                material_name,
                cat.broad,
                cat.high,
                cat.command,
                cat.name,
                "Sí" if cat.encj else "No",
                "Sí" if cat.mot else "No",
                "Sí" if cat.clnt else "No",
            )
            result.append((cat.id, name))
        return result

    # @api.constrains('broad', 'high', 'product_type', 'courtain_type')
    # def _check_values(self):
    #     for record in self:
    #         if record.product_type != 'service' and (record.broad <= 0.0 or record.high <= 0.0):
    #             raise ValidationError(_('Los valores de ancho o alto deben ser mayores a cero.'))

    @api.constrains('broad', 'high', 'courtain_type', 'ambience', 'command', 'material', 'product_details_ok', 'name', 'product_uom_qty')
    def _check_values(self):
        for record in self:
            if record.courtain_type or record.product_details_ok:
                missing_fields = []
                if not record.courtain_type:
                    missing_fields.append("Tipo cortina")
                if not record.ambience:
                    missing_fields.append("Ambiente")
                if not record.command:
                    missing_fields.append("Mando")
                if not record.material:
                    missing_fields.append("Material")
                if missing_fields:
                    missing_fields_str = ", ".join(missing_fields)
                    product_name = record.name or "Producto sin nombre"
                    raise ValidationError(
                        _('El producto "{}" tiene campos faltantes que son obligatorios: {}').format(product_name, missing_fields_str))
                if record.broad <= 0.0 or record.high <= 0.0:
                    raise ValidationError(_('Los valores de ancho o alto deben ser mayores a cero.'))
                if record.product_uom_qty <= 0.0:
                    raise ValidationError(_('No deben existir registros con cantidades menores a 1.'))


    # @api.onchange('material')
    # def _check_material_available(self):
    #     for record in self:
    #         # Verificar existencia en stock del material
    #         if record.material:
    #             product_qty_available = record.material.qty_available
    #             if product_qty_available <= 0:
    #                 raise ValidationError(
    #                     _('El material "{}" no tiene existencias en stock.').format(record.material.name))

    # @api.onchange('product_id')
    # def onchange_product_id(self):
    #     if self.product_type == 'service':
    #         self.product_uom_qty = 1

    # @api.model_create_multi
    # @api.returns('self', lambda value: value.id)
    # def create(self, vals_list):
    #     notes = super(SaleOrderLine, self).create(vals_list)
    #     for note in notes:
    #         sale_order_line = self.env['sale.order.line'].browse(
    #             self.env.context.get('sale_order_line'))
    #         sale_order_line.write({'details_id': note.id})
    #     return notes

    m2 = fields.Float(string="M2", compute="_compute_m2")

    @api.depends('broad', 'high')
    def _compute_m2(self):
        for record in self:
            record.m2 = record.broad * record.high

    order_id_extra = fields.Many2one(
        'sale.order', compute='_compute_order_id_extra', store=True)
    name_extra = fields.Char(
        compute='_compute_name_extra', store=True)
    product_id_extra = fields.Many2one(
        'product.product', compute='_compute_product_id_extra', store=True)
    quantity_extra = fields.Float(
        compute='_compute_quantity_extra', store=True)
    price_unit_extra = fields.Float(
        compute='_compute_price_unit_extra', store=True)
    price_subtotal_extra = fields.Float(
        compute='_compute_price_subtotal_extra', store=True)
    price_total_extra = fields.Float(
        compute='_compute_price_total_extra', store=True)

    @api.depends('order_id', 'name', 'product_id', 'product_uom_qty', 'price_unit', 'price_subtotal', 'price_total')
    def _compute_order_id_extra(self):
        for line in self:
            line.order_id_extra = line.order_id

    @api.depends('name', 'courtain_type')
    def _compute_name_extra(self):
        for line in self:
            if line.courtain_type:
                courtain_type = line.courtain_type
                line.name_extra = f"{line.name} ({courtain_type})"
            else:
                line.name_extra = line.name

    @api.depends('order_id', 'product_id')
    def _compute_product_id_extra(self):
        for line in self:
            line.product_id_extra = line.product_id

    @api.depends('product_uom_qty', 'broad', 'high')
    def _compute_quantity_extra(self):
        for line in self:
            if line.broad and line.high:
                line.quantity_extra = line.broad * line.high
            else:
                line.quantity_extra = line.product_uom_qty

    @api.depends('order_id', 'price_unit')
    def _compute_price_unit_extra(self):
        for line in self:
            line.price_unit_extra = line.price_unit

    @api.depends('order_id', 'price_subtotal')
    def _compute_price_subtotal_extra(self):
        for line in self:
            line.price_subtotal_extra = line.price_subtotal

    @api.depends('order_id', 'price_total')
    def _compute_price_total_extra(self):
        for line in self:
            line.price_total_extra = line.price_total

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def name_get(self):
        result = []
        for record in self:
            if record.class_inherit and record.class_inherit.cl_name == 'TELAS':
                name = record.name  # Solo muestra el nombre del producto
            else:
                name = record.name
            result.append((record.id, name))
        return result