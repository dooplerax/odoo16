from odoo import api, fields, models, _
from odoo.exceptions import (UserError)
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    dirEntrega=fields.Char(string="Direccion de entrega")
    
    def action_confirm(self):
        for line in self.order_line:
            if line.product_details_ok:
                if not line.details_id:
                    raise UserError(_('El producto %s requiere de detalles') % (line.product_id.name))
        sale = super(SaleOrder, self).action_confirm()
        
        return sale
            
             

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    product_details_ok = fields.Boolean(string='Product Details',related='product_template_id.details_ok')
    details_id = fields.Many2one('sale.order.pop', string='Detalle del producto',required=False, ondelete='cascade')
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
        

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'product_id.product_tmpl_id.m2')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'] * (line.product_id.product_template_id.m2 or 1),
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_product_id_check_availability(self):
        res = super(SaleOrderLine, self)._onchange_product_id_check_availability()
        self._compute_amount()
        return res
