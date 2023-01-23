from odoo import api, fields, models, _


class SaleOrderPop(models.Model):
    _inherit = ['sale.order']
    cortinas_ids = fields.One2many('sale.order.pop', 'cortinas_id', string='Descripción')
    details_ok=fields.Boolean(string='Permite Detalle',default=True)

    def generate_details_code(self):
        try:

            code = "{}-{}-{}-{}-{}-{}-{}-{}".format(
                self.cortinas_ids.tipo_cortina,
                self.cortinas_ids.ancho,
                self.cortinas_ids.alto,
                self.cortinas_ids.ambiente,
                self.cortinas_ids.enci,
                self.cortinas_ids.mot,
                self.cortinas_ids.clnt,
                        
            )
            return code
        except Exception as e:
            return "validar"


    detail_descripcion=fields.Char(string='Descripción',default=generate_details_code)




    

    



