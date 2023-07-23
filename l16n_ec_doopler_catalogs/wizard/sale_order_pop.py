from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleOrderPop(models.Model):
    _name = 'sale.order.pop'

    # cortinas_id = fields.Many2one('sale.order', string='ID CORTINA', required=True)    
    name = fields.Char(string="Ambiente", required=True)
    tipo_cortina = fields.Selection(
        [('roller', 'Roller'), ('romana', 'Romana'), ('panelada', 'Panelada'), ('claraboya', 'Claraboya'),
         ('triple', 'Triple'), ('shade', 'Shade'), ('diungunce', 'Diungunce')], string="Tipo Cortina", required=True)
    material = fields.Many2one("product.template", domain="[('class_inherit.cl_name','=','TELAS')]")
    ancho = fields.Float(string="Ancho", required=True, default=None)
    alto = fields.Float(string="Alto", required=True, default=None)
    mando = fields.Selection([('Izquierda', 'IZQUIERDA'), ('Derecha', 'DERECHA'), ('Ambos', 'AMBOS')], string="Mando", required=True)
    # ambiente = fields.Char(string="Ambiente", required=True)
    encj = fields.Boolean(string="ENCJ.", required=True, default=False)
    mot = fields.Boolean(string="MOT.", required=True, default=False)
    clnt = fields.Boolean(string="CLNT.", required=True, default=False)

    def name_get(self):
        result = []
        for cat in self:
            material_name = cat.material.name if cat.material else ""
            name = "Tipo de cortina: {} / Materiales: {} / Ancho: {} / Alto: {} / Mando: {} / Ambiente: {} / ENCJ.: {} / MOT.: {} /  CLNT.: {}".format(
                cat.tipo_cortina,
                material_name,
                cat.ancho,
                cat.alto,
                cat.mando,
                cat.name,
                "Sí" if cat.encj else "No",
                "Sí" if cat.mot else "No",
                "Sí" if cat.clnt else "No",
            ) 
            result.append((cat.id, name))
        return result

    @api.constrains('ancho', 'alto')
    def _check_values(self):
        if self.ancho <= 0.0 or self.alto <= 0.0:
            raise ValidationError(_('Los valores deben ser mayores a cero.'))

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        note = super(SaleOrderPop, self).create(vals_list)
        sale_order_line = self.env['sale.order.line'].browse(self.env.context.get('sale_order_line'))
        sale_order_line.write({'details_id': note.id})
        return note
    
    m2 = fields.Float(string="M2", compute="_compute_m2")

    @api.depends('ancho', 'alto')
    def _compute_m2(self):
        for record in self:
            record.m2 = record.ancho * record.alto
