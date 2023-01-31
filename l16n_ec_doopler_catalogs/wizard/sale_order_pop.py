from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleOrderPop(models.Model):
    _name = 'sale.order.pop'
    
    # cortinas_id = fields.Many2one('sale.order', string='ID CORTINA', required=True)    
    tipo_cortina=fields.Selection([('roller','Roller'),('romana','Romana'),('panelada','Panelada'),('claraboya','Claraboya'),('triple','Triple'),('shade','Shade'),('diungunce','Diungunce')], string="Tipo Cortina",required=True)
    material = fields.Many2one('cproduct.doclass', string="Material",required=True)
    ancho=fields.Float(string="Ancho",required=True,default=None)
    alto=fields.Float(string="Alto",required=True,default=None)
    mando=fields.Selection([('Izquierda','IZQUIERDA'),('Derecha','DERECHA')], string="Mando",required=True)
    ambiente=fields.Char(string="Ambiente",required=True)
    enci=fields.Boolean(string="Enci",required=True, default=False)
    mot=fields.Boolean(string="Mot",required=True, default=False)
    clnt=fields.Boolean(string="Clnt",required=True, default=False)

    def name_get(self):
        result = []
        for cat in self:
            name = "Tipo de cortina: {} / Materiales: {} / Ancho: {} / Alto: {} / Mando: {} / Ambiente: {} / Encj: {} / Mot: {} /  Clnt: {}".format(
                cat.tipo_cortina,
                cat.material,
                cat.ancho,
                cat.alto,
                cat.mando,
                cat.ambiente,
                cat.enci,
                cat.mot,
                cat.clnt,
            ) 
            result.append((cat.id, name))
        return result
    @api.constrains('ancho', 'alto')
    def _check_values(self):
        if self.ancho <= 0.0 or self.alto <= 0.0:
            raise ValidationError(_('Los valores deben ser mayores a cero.'))

    # product_id = fields.Many2one('product.template',string="product_id")
    # default_code=fields.Char('product.template',related='product_id.default_code')