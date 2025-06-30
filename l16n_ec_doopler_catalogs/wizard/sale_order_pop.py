from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderPop(models.Model):
    _name = 'sale.order.pop'
    _description = 'Descripción'
    
    # # cortinas_id = fields.Many2one('sale.order', string='ID CORTINA', required=True)
    # name = fields.Char(string="Ambiente", required=True)
    # tipo_cortina = fields.Selection(
    #     selection='_get_tipo_cortina_options', string="Tipo Cortina", required=True
    # )
    # material = fields.Many2one(
    #     "product.template", domain="[('class_inherit.cl_name','=','TELAS')]")
    # ancho = fields.Float(string="Ancho", required=True, default=None)
    # alto = fields.Float(string="Alto", required=True, default=None)
    # mando = fields.Selection([('Izquierda', 'IZQUIERDA'), ('Derecha',
    #                          'DERECHA'), ('Ambos', 'AMBOS')], string="Mando", required=True)
    # # ambiente = fields.Char(string="Ambiente", required=True)
    # encj = fields.Boolean(string="ENCJ.", required=True, default=False)
    # mot = fields.Boolean(string="MOT.", required=True, default=False)
    # clnt = fields.Boolean(string="CLNT.", required=True, default=False)
    #
    # @api.model
    # def _get_tipo_cortina_options(self):
    #     return [
    #         ('enrollable', 'Enrollable'),
    #         ('zebra', 'Zebra'),
    #         ('romana', 'Romana'),
    #         ('panelada', 'Panelada'),
    #         ('claraboya', 'Claraboya'),
    #         ('triple_shade', 'Triple Shade'),
    #         ('divergence', 'Divergence'),
    #         ('tradicional', 'Tradicional'),
    #         ('horizontal', 'Horizontal'),
    #         ('vertical', 'Vertical'),
    #         ('tradicional_onda_perfecta', 'Tradicional onda perfecta'),
    #         ('tradicional_con_pliegues', 'Tradicional con pliegues'),
    #     ]

    # def name_get(self):
    #     result = []
    #     for cat in self:
    #         material_name = cat.material.name if cat.material else ""
    #         name = "Tipo de cortina: {} / Materiales: {} / Ancho: {} / Alto: {} / Mando: {} / Ambiente: {} / ENCJ.: {} / MOT.: {} /  CLNT.: {}".format(
    #             cat.tipo_cortina,
    #             material_name,
    #             cat.ancho,
    #             cat.alto,
    #             cat.mando,
    #             cat.name,
    #             "Sí" if cat.encj else "No",
    #             "Sí" if cat.mot else "No",
    #             "Sí" if cat.clnt else "No",
    #         )
    #         result.append((cat.id, name))
    #     return result

    # @api.constrains('ancho', 'alto')
    # def _check_values(self):
    #     if self.ancho <= 0.0 or self.alto <= 0.0:
    #         raise ValidationError(_('Los valores deben ser mayores a cero.'))

    # @api.model_create_multi
    # @api.returns('self', lambda value: value.id)
    # def create(self, vals_list):
    #     note = super(SaleOrderPop, self).create(vals_list)
    #     sale_order_line = self.env['sale.order.line'].browse(
    #         self.env.context.get('sale_order_line'))
    #     sale_order_line.write({'details_id': note.id})
    #     return note

    m2 = fields.Float(string="M2", compute="_compute_m2")

    # @api.depends('ancho', 'alto')
    # def _compute_m2(self):
    #     for record in self:
    #         record.m2 = record.ancho * record.alto


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    m2 = fields.Float(string="M2", compute='_compute_m2', store=True)

    @api.depends('broad', 'high', 'product_uom_qty')
    def _compute_m2(self):
        for line in self:
            line.m2 = line.broad * line.high * line.product_uom_qty

    @api.depends('m2', 'product_uom_qty')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.m2:
                line.product_uom_qty = line.m2
            else:
                super(SaleOrderLine, line)._compute_product_uom_qty()
    # Codigo para generar número de orden en cotización, se comenta por correcciones del ticket 2868
    """ orden = fields.Char(string="Orden", readonly=True, store=True, default='')
    latest_order_number = fields.Integer(
        string="Latest Order Number", compute="_compute_latest_order_number", store=True)

    @api.depends('orden')
    def _compute_latest_order_number(self):
        for record in self:
            if record.orden and record.orden.isdigit():
                record.latest_order_number = int(record.orden)
            else:
                record.latest_order_number = 0

    @api.model
    def create(self, vals):
        latest_order_number = self.env['sale.order.line'].search(
            [], order='latest_order_number desc', limit=1)
        next_order_number = latest_order_number.latest_order_number + 1

        vals['orden'] = str(next_order_number).zfill(5)
        new_record = super(SaleOrderLine, self).create(vals)

        return new_record """

    items = fields.Integer(string="Items", compute="_compute_items", store=True)

    @api.depends('order_id')
    def _compute_items(self):
        for order in self.mapped('order_id'):
            order_lines = order.order_line.filtered(lambda x: x.display_type not in ['line_note', 'line_section']).sorted('sequence')
            for index, line in enumerate(order_lines):
                line.items = index + 1


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    name = fields.Char(string="Título", default="Nuevo Registro", readonly=True)

    def get_group_totals(self):
        groups = {}

        for line in self.order_line:
            if line.display_type in ['line_section', 'line_note']:
                continue

            # Definir la clave de agrupación
            group_key = (
                line.courtain_type or '',
                line.material.name if line.material else line.product_id_extra.name
            )

            if group_key not in groups:
                groups[group_key] = {
                    'courtain_type': line.courtain_type,
                    'name': line.material.name if line.material else line.product_id_extra.name,
                    'quantity_extra': 0.0,
                    'price_subtotal_extra': 0.0,
                    'price_total_extra': 0.0,
                    'price_unit': line.price_unit,
                    'display_type': line.display_type,
                }

            # Sumar valores
            groups[group_key]['quantity_extra'] += line.quantity_extra
            groups[group_key]['price_subtotal_extra'] += line.price_subtotal_extra
            groups[group_key]['price_total_extra'] += line.price_total_extra

        return list(groups.values())
