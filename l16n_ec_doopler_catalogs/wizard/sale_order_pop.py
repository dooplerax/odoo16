from odoo import api, fields, models, _


class SaleOrderPop(models.Model):
    _name = 'sale.order.pop'
    
    # cortinas_id = fields.Many2one('sale.order', string='ID CORTINA', required=True)    
    tipo_cortina=fields.Selection([('roller','Roller'),('romana','Romana'),('panelada','Panelada'),('claraboya','Claraboya'),('triple','Triple'),('shade','Shade'),('diungunce','Diungunce')], string="Tipo Cortina",required=True)
    material=fields.Selection([('producto2','PRODUCTO 2'),('producto3','PRODUCTO 3')], string="Material",required=True)
    ancho=fields.Float(string="Ancho",required=True)
    alto=fields.Float(string="Alto",required=True)
    ambiente=fields.Char(string="Ambiente",required=True)
    enci=fields.Boolean(string="Enci",required=True, default=False)
    mot=fields.Boolean(string="Mot",required=True, default=False)
    clnt=fields.Boolean(string="Clnt",required=True, default=False)

    def name_get(self):
        result = []
        for cat in self:
            name = "Tipo de cortina: {} / Materiales: {} / Ancho: {} / Alto: {} / Mando: -- / Ambiente: {} / Encj: {} / Mot: {} /  Clnt: {}".format(
                cat.tipo_cortina,
                cat.material,
                cat.ancho,
                cat.alto,
                cat.ambiente,
                cat.enci,
                cat.mot,
                cat.clnt,
            ) 
            result.append((cat.id, name))
        return result


    # product_id = fields.Many2one('product.template',string="product_id")
    # default_code=fields.Char('product.template',related='product_id.default_code')