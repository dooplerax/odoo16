from odoo import api, fields, models

from odoo.osv import expression
from collections import defaultdict


class StockMove(models.Model):
    _inherit = 'stock.move'

    quantity_done = fields.Float(
        'Quantity Done', compute='_quantity_done_compute', digits='Product Unit of Measure',
        inverse='_quantity_done_set', store=True)

    @api.depends('move_line_ids.qty_done', 'move_line_ids.quantity_done_times_factor_inv',
                 'move_line_nosuggest_ids.qty_done')
    def _quantity_done_compute(self):
        if not any(self._ids):
            # onchange
            for move in self:
                move.quantity_done = move._quantity_done_sml()
        else:
            # compute
            move_lines_ids = set()
            for move in self:
                move_lines_ids |= set(move._get_move_lines().ids)

            data = self.env['stock.move.line']._read_group(
                [('id', 'in', list(move_lines_ids))],
                ['move_id', 'quantity_done_times_factor_inv', 'qty_done'],
                ['move_id', 'quantity_done_times_factor_inv'],
                lazy=False
            )

            rec = defaultdict(list)
            for d in data:
                rec[d['move_id'][0]] += [(d['quantity_done_times_factor_inv'], d['qty_done'])]

            for move in self:
                uom = move.product_uom
                move.quantity_done = sum(
                    qty * factor_inv for factor_inv, qty in rec.get(move.ids[0] if move.ids else move.id, [])
                )

    def _quantity_done_sml(self):
        self.ensure_one()
        quantity = 0
        for move_line in self._get_move_lines():
            quantity += move_line.quantity_done_times_factor_inv
        return quantity


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_uom_d = fields.Many2one(
        'uom.uom', 'Unidad de medida',
        readonly=False, related='product_id.uom_po_id', store=True)

    quantity_done_times_factor_inv = fields.Float(
        string='Quantity Done',
        compute='_compute_quantity_done_times_factor_inv',
        store=True
    )

    @api.depends('qty_done', 'product_id.uom_po_id')
    def _compute_quantity_done_times_factor_inv(self):
        for record in self:
            if record.product_id and record.product_id.uom_po_id:
                record.quantity_done_times_factor_inv = record.qty_done * record.product_id.uom_po_id.factor_inv
            else:
                record.quantity_done_times_factor_inv = 0.0

    @api.onchange('qty_done', 'product_id')
    def _onchange_qty_done(self):
        res = {}
        # if self.qty_done and self.product_id.tracking == 'serial':
        #     qty_done = self.product_uom_id._compute_quantity(self.qty_done, self.product_id.uom_id)
        #     if float_compare(qty_done, 1.0, precision_rounding=self.product_id.uom_id.rounding) != 0:
        #         message = _('You can only process 1.0 %s of products with unique serial number.',
        #                     self.product_id.uom_id.name)
        #         res['warning'] = {'title': _('Warning'), 'message': message}
        if self.product_id:
            # Autocomplete the product_uom_id field with the uom_po_id value of the product
            self.product_uom_id = self.product_id.uom_po_id.id
        return res

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
