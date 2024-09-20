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
    costumer = fields.Char(string='Customer')
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
    production_date = fields.Date(string='Production date', required=False)
    production_table = fields.Many2one('mrp.workcenter', string='Production table', required=False)
    quotation_note = fields.Text(string='Quotation note')
    production_note = fields.Text(string='Production note')
    sale_id = fields.Many2one('sale.order', string="Cotización")

class StockMove(models.Model):
    _inherit = 'stock.move'

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, required=True, precompute=True)
    courtain_type = fields.Selection(
        selection='_get_tipo_cortina_options', string="Tipo Cortina")
    ambience = fields.Char(string="Ambiente")
    command = fields.Selection(
        selection='_get_command_selection',
        string="Mando"
    )
    material = fields.Many2one(
        "product.template", string="Material")
    broad = fields.Float(string="Ancho", default=None, digits=(16, 3))
    high = fields.Float(string="Alto", default=None, digits=(16, 3))
    encj = fields.Boolean(string="ENCJ.", default=False)
    mot = fields.Boolean(string="MOT.", default=False)
    clnt = fields.Boolean(string="CINT.", default=False)

    quantity = fields.Float(
        string="Quantity",
        compute='calculated_quantity_field',
        digits=(16, 3), default=0.0,
        store=True, readonly=False, required=True, precompute=True)

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if not line.product_id:
                continue
            lang = line.order_id._get_lang()
            if lang != self.env.lang:
                line = line.with_context(lang=lang)
            name = line._get_sale_order_line_multiline_description_sale()
            if line.is_downpayment and not line.display_type:
                context = {'lang': lang}
                dp_state = line._get_downpayment_state()
                if dp_state == 'draft':
                    name = _("%(line_description)s (Draft)", line_description=name)
                elif dp_state == 'cancel':
                    name = _("%(line_description)s (Canceled)", line_description=name)
                del context
            line.name = name

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

    def _get_command_selection(self):
        return [
            ('Izquierda', 'IZQUIERDO'),
            ('Derecha', 'DERECHO'),
            ('Ambos', 'AMBOS'),
            ('Fijo', 'FIJA')
        ]

    # @api.constrains('broad', 'high', 'courtain_type', 'ambience', 'command', 'material', 'product_id')
    # def _check_values_confirm(self):
    #     for record in self:
    #         if record.courtain_type or record.product_id:
    #             missing_fields = []
    #             if not record.courtain_type:
    #                 missing_fields.append("Tipo cortina")
    #             if not record.ambience:
    #                 missing_fields.append("Ambiente")
    #             if not record.command:
    #                 missing_fields.append("Mando")
    #             if not record.material:
    #                 missing_fields.append("Material")
    #             if missing_fields:
    #                 missing_fields_str = ", ".join(missing_fields)
    #                 product_name = record.product_id.name or "Producto sin nombre"
    #                 raise ValidationError(
    #                     _('El producto "{}" tiene campos faltantes que son obligatorios: {}').format(product_name,
    #                                                                                                  missing_fields_str))
    #             if record.broad <= 0.0 or record.high <= 0.0:
    #                 raise ValidationError(_('Los valores de ancho o alto deben ser mayores a cero.'))
    #             if record.product_uom_qty <= 0.0:
    #                 raise ValidationError(_('No deben existir registros con cantidades menores a 1.'))

    @api.depends('broad', 'high')
    @api.onchange('product_id')
    def calculated_quantity_field(self):
        for record in self:
            if (record.broad <= 0.0 or record.high <= 0.0):
                record.quantity = 1
            else:
                record.quantity = record.broad * record.high


