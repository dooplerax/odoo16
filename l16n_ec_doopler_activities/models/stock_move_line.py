from odoo import api, fields, models

from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero

from importlib.resources import _


class StockMove(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('qty_done', 'product_uom_id')
    def _onchange_qty_done(self):
        # res = {}
        # if self.qty_done and self.product_id.tracking == 'serial':
        #     qty_done = self.product_uom_id._compute_quantity(self.qty_done, self.product_id.uom_id)
        #     if float_compare(qty_done, 1.0, precision_rounding=self.product_id.uom_id.rounding) != 0:
        #         message = _('You can only process 1.0 %s of products with unique serial number.', self.product_id.uom_id.name)
        #         res['warning'] = {'title': _('Warning'), 'message': message}
        return {}

class StockQuantValidate(models.Model):
        _inherit = 'stock.quant'
        @api.constrains('quantity')
        def check_quantity(self):
            sn_quants = self.filtered(
                lambda q: q.product_id.tracking == 'serial' and q.location_id.usage != 'inventory' and q.lot_id)
            if not sn_quants:
                return
            domain = expression.OR([
                [('product_id', '=', q.product_id.id), ('location_id', '=', q.location_id.id), ('lot_id', '=', q.lot_id.id)]
                for q in sn_quants
            ])
            groups = self.read_group(
                domain,
                ['quantity'],
                ['product_id', 'location_id', 'lot_id'],
                orderby='id',
                lazy=False,
            )
            for group in groups:
                product = self.env['product.product'].browse(group['product_id'][0])
                lot = self.env['stock.lot'].browse(group['lot_id'][0])
                uom = product.uom_id
                # if float_compare(abs(group['quantity']), 1, precision_rounding=uom.rounding) > 0:
                #     raise ValidationError(
                #         _('The serial number has already been assigned: \n Product: %s, Serial Number: %s') % (
                #         product.display_name, lot.name))
