from odoo import api, fields, models, _
from odoo.exceptions import (UserError)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dirEntrega = fields.Char(string="Direccion de entrega")

    def action_confirm(self):
        for line in self.order_line:
            if line.product_details_ok:
                if not line.details_id:
                    raise UserError(
                        _('El producto %s requiere de detalles') % (line.product_id.name))
        sale = super(SaleOrder, self).action_confirm()

        return sale


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_details_ok = fields.Boolean(
        string='Product Details', related='product_template_id.details_ok')
    metros2 = fields.Float(related='product_template_id.m2')
    details_id = fields.Many2one(
        'sale.order.pop', string='Detalle del producto', required=False, ondelete='cascade')
    details_name = fields.Char(string='Descripción')

    def create_details(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.pop',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'sale_order_line': self.id},
            'res_id': self.details_id.id,
            'id': self.details_id.id,
        }

    order_id_extra = fields.Many2one(
        'sale.order', string='Order Extra', compute='_compute_order_id_extra', store=True)
    name_extra = fields.Char(string='Description',
                             compute='_compute_name_extra', store=True)
    product_id_extra = fields.Many2one(
        'product.product', string='Material', compute='_compute_product_id_extra', store=True)
    quantity_extra = fields.Float(
        string='Cantidad', compute='_compute_quantity_extra', store=True)
    price_unit_extra = fields.Float(
        string='Precio Unitario', compute='_compute_price_unit_extra', store=True)
    price_subtotal_extra = fields.Float(
        string='Subtotal', compute='_compute_price_subtotal_extra', store=True)
    price_total_extra = fields.Float(
        string='Total', compute='_compute_price_total_extra', store=True)

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
