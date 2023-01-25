from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    product_details_ok = fields.Boolean(string='Product Details',related='product_template_id.details_ok')
    details_id = fields.Many2one('sale.order.pop', string='Descripción',required=False)



