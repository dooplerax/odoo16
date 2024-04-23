from odoo import api, fields, models, _
from odoo.exceptions import (UserError)
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dirEntrega = fields.Char(string="Direccion de entrega")
    customer = fields.Char(string="Customer ")

    # def action_confirm(self):
    #     for line in self.order_line:
    #         if line.product_details_ok:
    #             if not line.details_id:
    #                 raise UserError(
    #                     _('El producto %s requiere de detalles') % (line.product_id.name))
    #     sale = super(SaleOrder, self).action_confirm()
    #
    #     return sale


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = "Descripción"
    product_details_ok = fields.Boolean(
        string='Product Details', related='product_template_id.details_ok')
    details_id = fields.Many2one(
        'sale.order.pop', string='Detalle del producto', required=False, ondelete='cascade')
    details_name = fields.Char(string='Descripción')

    ambience = fields.Char(string="Ambiente")
    courtain_type = fields.Selection(
        selection='_get_tipo_cortina_options', string="Tipo Cortina")
    material = fields.Many2one(
        "product.template", domain="[('class_inherit.cl_name','=','TELAS')]")
    broad = fields.Float(string="Ancho", default=None)
    high = fields.Float(string="Alto", default=None)
    command = fields.Selection([('Izquierda', 'IZQUIERDA'), ('Derecha',
                                                           'DERECHA'), ('Ambos', 'AMBOS')], string="Mando")
    # ambiente = fields.Char(string="Ambiente", required=True)
    encj = fields.Boolean(string="ENCJ.", default=False)
    mot = fields.Boolean(string="MOT.", default=False)
    clnt = fields.Boolean(string="CLNT.", default=False)

    product_uom_qty = fields.Float(
        string="Quantity",
        compute='calculated_quantity_field',
        digits='Product Unit of Measure', default=0.0,
        store=True, readonly=False, required=True, precompute=True)

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
        ]

    @api.depends('broad', 'high')
    def calculated_quantity_field(self):
        for record in self:
            record.product_uom_qty = record.broad * record.high

    @api.constrains('product_details_ok', 'courtain_type', 'ambience', 'command', 'material', 'broad', 'high', 'clnt',
                    'mot', 'encj')
    def _check_required_fields(self):
        for record in self:
            if record.product_details_ok:
                if not record.courtain_type or not record.ambience or not record.command or not record.material or not record.broad or not record.high or not record.clnt or not record.mot or not record.encj:
                    raise ValidationError(
                        "Por favor, complete todos los campos requeridos antes de agregar otra línea.")

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

    @api.constrains('broad', 'high')
    def _check_values(self):
        for record in self:
            if record.broad <= 0.0 or record.high <= 0.0:
                raise ValidationError(_('Los valores de ancho o alto deben ser mayores a cero.'))

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        notes = super(SaleOrderLine, self).create(vals_list)
        for note in notes:
            sale_order_line = self.env['sale.order.line'].browse(
                self.env.context.get('sale_order_line'))
            sale_order_line.write({'details_id': note.id})
        return notes

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

    @api.depends('name', 'details_id', 'details_id.tipo_cortina')
    def _compute_name_extra(self):
        for line in self:
            if line.details_id and line.details_id.tipo_cortina:
                tipo_cortina = line.details_id.tipo_cortina
                line.name_extra = f"{line.name} ({tipo_cortina})"
            else:
                line.name_extra = line.name

    @api.depends('order_id', 'product_id')
    def _compute_product_id_extra(self):
        for line in self:
            line.product_id_extra = line.product_id

    @api.depends('product_uom_qty', 'details_id.m2')
    def _compute_quantity_extra(self):
        for line in self:
            if line.details_id:
                line.quantity_extra = line.details_id.m2
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
