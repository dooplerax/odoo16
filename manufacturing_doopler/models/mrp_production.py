from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="""[
                ('type', 'in', ['product', 'consu']),
                '|',
                    ('company_id', '=', False),
                    ('company_id', '=', company_id)
            ]
            """,
        compute='_compute_product_id', store=True, copy=True, precompute=True,
        readonly=True, required=False, check_company=True,
        states={'draft': [('readonly', False)]})

    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=False, required=False, compute='_compute_uom_id', store=True, copy=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")

    client = fields.Many2one('res.partner', string='Client', required=True)
    costumer = fields.Char(string='Costumer')
    user_input = fields.Selection(
        selection=lambda self: [(user.id, user.name) for user in self.env['res.users'].search([])],
        string='User input', required=True, help="User who created the production order")

    entry_date = fields.Datetime(string='Entry date', required=True, default=fields.Datetime.now)
    delivery_date = fields.Datetime(string='Delivery date', required=True)
    installation_req = fields.Selection(
        [('yes', 'Sí'), ('no', 'No')], string='Installation Req.', required=True)
    shift = fields.Selection(
        [('day', 'Diurno'), ('night', 'Nocturno')], string='Turn', required=True)
    delivery_address = fields.Text(string='Delivery address', required=True)
    production_date = fields.Date(string='Production date', required=True)
    production_table = fields.Many2one('mrp.workcenter', string='Production table', required=True)
    quotation_note = fields.Text(string='Quotation note')
    production_note = fields.Text(string='Production note')
