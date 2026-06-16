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
                active_lines = move._get_move_lines().filtered(
                    lambda l: l.state not in ('cancel',)
                )
                move_lines_ids |= set(active_lines.ids)

            data = self.env['stock.move.line']._read_group(
                [('id', 'in', list(move_lines_ids))],
                ['move_id', 'qty_done'],
                ['move_id'],
                lazy=False
            )

            rec = defaultdict(float)
            for d in data:
                rec[d['move_id'][0]] += d['qty_done']

            for move in self:
                move.quantity_done = rec.get(move.ids[0] if move.ids else move.id, 0.0)

    def _quantity_done_sml(self):
        self.ensure_one()
        quantity = 0
        for move_line in self._get_move_lines():
            quantity += move_line.qty_done
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
        if self.product_id:
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