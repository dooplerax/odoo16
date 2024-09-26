from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext
import logging
_logger = logging.getLogger(__name__)

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
    user_input = fields.Many2one('res.users', string='User input', readonly=False, default=False)

    entry_date = fields.Datetime(string='Entry date', required=True, default=fields.Datetime.now)
    delivery_date = fields.Datetime(string='Delivery date', required=True)
    installation_req = fields.Selection(
        [('yes', 'Sí'), ('no', 'No')], string='Installation Req.', required=False)
    shift = fields.Selection(
        [('day', 'Diurno'), ('night', 'Nocturno')], string='Turn', required=False)
    delivery_address = fields.Text(string='Delivery address', required=True)
    production_date = fields.Date(string='Production date', required=False)
    production_table = fields.Many2one('mrp.workcenter', string='Production table', required=False)
    quotation_note = fields.Text(string='Quotation note')
    production_note = fields.Text(string='Production note')
    sale_id = fields.Many2one('sale.order', string="Cotización")

    en_ct = fields.Integer(string="EN", compute="_compute_curtain_counts", help="Tipo de cortina Enrollable", readonly=True)
    ze_ct = fields.Integer(string="ZE", compute="_compute_curtain_counts", help="Tipo de cortina Zebra", readonly=True)
    ro_ct = fields.Integer(string="RO", compute="_compute_curtain_counts", help="Tipo de cortina Romana", readonly=True)
    pa_ct = fields.Integer(string="PA", compute="_compute_curtain_counts", help="Tipo de cortina Panelada", readonly=True)
    cla_ct = fields.Integer(string="CLA", compute="_compute_curtain_counts", help="Tipo de cortina Claraboya", readonly=True)
    tsh_ct = fields.Integer(string="TSH", compute="_compute_curtain_counts", help="Tipo de cortina Triple Shade", readonly=True)
    di_ct = fields.Integer(string="DI", compute="_compute_curtain_counts", help="Tipo de cortina Divergence", readonly=True)
    trad_ct = fields.Integer(string="TRAD", compute="_compute_curtain_counts", help="Tipo de cortina Tradicional", readonly=True)
    horz_ct = fields.Integer(string="HORZ", compute="_compute_curtain_counts", help="Tipo de cortina Horizontal", readonly=True)
    vert_ct = fields.Integer(string="VERT", compute="_compute_curtain_counts", help="Tipo de cortina Vertical", readonly=True)
    top_ct = fields.Integer(string="TOP", compute="_compute_curtain_counts", help="Tipo de cortina Tradicional Onda Perfecta", readonly=True)
    tcp_ct = fields.Integer(string="TCP", compute="_compute_curtain_counts", help="Tipo de cortina Tradicional Con Pliegues", readonly=True)

    encj_count = fields.Integer(string="ENCJ Activos", compute='_compute_encj_mot_clnt_count', store=True)
    mot_count = fields.Integer(string="MOT Activos", compute='_compute_encj_mot_clnt_count', store=True)
    clnt_count = fields.Integer(string="CINT Activos", compute='_compute_encj_mot_clnt_count', store=True)

    status_custom = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirm_custom', 'Confirmado'),
            ('cancel_custom', 'Cancelado'),
            ('progress', 'En Progreso'),
            ('done', 'Terminado'),
        ],
        string='Estado de la orden',
        default='draft',
    )

    total_curtains = fields.Integer(string='Total de Cortinas', compute='_compute_total_curtains', store=True)

    @api.depends('move_raw_ids')
    def _compute_total_curtains(self):
        for record in self:
            total = sum(1 for move in record.move_raw_ids if move.product_id)
            record.total_curtains = total

    def action_view_sale_order(self):
        self.ensure_one()
        if self.sale_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Order',
                'res_model': 'sale.order',
                'res_id': self.sale_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    @api.depends('move_raw_ids.courtain_type')
    def _compute_curtain_counts(self):
        for production in self:
            en_ct = ze_ct = ro_ct = pa_ct = cla_ct = tsh_ct = di_ct = trad_ct = horz_ct = vert_ct = top_ct = tcp_ct = 0

            for line in production.move_raw_ids:
                if line.courtain_type == 'enrollable':
                    en_ct += 1
                elif line.courtain_type == 'zebra':
                    ze_ct += 1
                elif line.courtain_type == 'romana':
                    ro_ct += 1
                elif line.courtain_type == 'panelada':
                    pa_ct += 1
                elif line.courtain_type == 'claraboya':
                    cla_ct += 1
                elif line.courtain_type == 'triple_shade':
                    tsh_ct += 1
                elif line.courtain_type == 'divergence':
                    di_ct += 1
                elif line.courtain_type == 'tradicional':
                    trad_ct += 1
                elif line.courtain_type == 'horizontal':
                    horz_ct += 1
                elif line.courtain_type == 'vertical':
                    vert_ct += 1
                elif line.courtain_type == 'tradicional_onda_perfecta':
                    top_ct += 1
                elif line.courtain_type == 'tradicional_con_pliegues':
                    tcp_ct += 1

            production.en_ct = en_ct
            production.ze_ct = ze_ct
            production.ro_ct = ro_ct
            production.pa_ct = pa_ct
            production.cla_ct = cla_ct
            production.tsh_ct = tsh_ct
            production.di_ct = di_ct
            production.trad_ct = trad_ct
            production.horz_ct = horz_ct
            production.vert_ct = vert_ct
            production.top_ct = top_ct
            production.tcp_ct = tcp_ct

    @api.depends('move_raw_ids.encj', 'move_raw_ids.mot', 'move_raw_ids.clnt')
    def _compute_encj_mot_clnt_count(self):
        for production in self:
            encj_count = 0
            mot_count = 0
            clnt_count = 0

            for line in production.move_raw_ids:
                if line.encj:
                    encj_count += 1
                if line.mot:
                    mot_count += 1
                if line.clnt:
                    clnt_count += 1

            production.encj_count = encj_count
            production.mot_count = mot_count
            production.clnt_count = clnt_count

    def action_confirm_custom(self):
        self.write({'status_custom': 'confirm_custom'})

    def action_cancel_custom(self):
        self.write({'status_custom': 'cancel_custom'})

    def action_mark_as_done(self):
        self.write({'status_custom': 'done'})

    def print_production_report(self):
        return self.env.ref('manufacturing_doopler.order_prod_report').report_action(self)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if any(production.status_custom == 'done' for production in self):
            raise UserError(_('Cannot delete a manufacturing order in done state.'))
        not_cancel = self.filtered(lambda m: m.status_custom != 'cancel_custom')
        if not_cancel:
            productions_name = ', '.join([prod.display_name for prod in not_cancel])
            raise UserError(_('%s cannot be deleted. Try to cancel them before.', productions_name))

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

    @api.depends('broad', 'high')
    @api.onchange('product_id')
    def calculated_quantity_field(self):
        for record in self:
            if (record.broad <= 0.0 or record.high <= 0.0):
                record.quantity = 1
            else:
                record.quantity = record.broad * record.high

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    production_order_count = fields.Integer(
        string="Production Orders",
        compute='_compute_production_order_count',
        store=False
    )

    production_order_confirmed = fields.Boolean(compute='_compute_production_order_confirmed')

    @api.depends('name')
    def _compute_production_order_confirmed(self):
        for order in self:
            production_orders = self.env['mrp.production'].search([('sale_id', '=', order.id)])
            confirmed = any(prod.status_custom == 'done' for prod in production_orders)
            order.production_order_confirmed = confirmed

    @api.depends('name')
    def _compute_production_order_count(self):
        for order in self:
            order.production_order_count = self.env['mrp.production'].search_count([('sale_id', '=', order.id)])

    def action_view_mrp_productions(self):
        self.ensure_one()
        production_orders = self.env['mrp.production'].search([('sale_id', '=', self.id)])

        current_user = self.env.user
        user_billing_location = current_user.billing_location
        if user_billing_location and user_billing_location.state_id.name == 'Pichincha':

            # Verificar si hay órdenes de producción
            for order in production_orders:
                if not order.installation_req or not order.shift:
                    # Si falta información, abre un popup
                    return {
                        'name': 'Complete Production Order',
                        'type': 'ir.actions.act_window',
                        'res_model': 'production.order.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_order_id': order.id,
                        }
                    }

            return {
                'type': 'ir.actions.act_window',
                'name': 'Ordenes de producción',
                'view_mode': 'tree,form',
                'res_model': 'mrp.production',
                'domain': [('sale_id', '=', self.id)],
                'context': dict(self.env.context),
            }
        else:
            raise ValidationError("Solo usuarios de Quito pueden acceder a ordenes de producción")

class ProductionOrderWizard(models.TransientModel):
    _name = 'production.order.wizard'

    installation_req = fields.Selection(
        [('yes', 'Sí'), ('no', 'No')], string='Installation Req.', required=True
    )
    shift = fields.Selection(
        [('day', 'Diurno'), ('night', 'Nocturno')], string='Turn', required=True
    )
    user_id = fields.Many2one('res.users', string='Usuario Responsable', readonly=True, default=lambda self: self.env.user)
    order_id = fields.Many2one('mrp.production', string='Orden de Producción')

    def action_save(self):
        if self.order_id:
            self.order_id.write({
                'installation_req': self.installation_req,
                'shift': self.shift,
                'user_input': self.user_id.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    enable_production_order = fields.Boolean(string='Habilitar órdenes de producción', default=False)