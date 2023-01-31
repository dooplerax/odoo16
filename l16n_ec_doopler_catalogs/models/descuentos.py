from odoo import fields, models,api,_
from odoo.exceptions import ValidationError
from datetime import date




class Descuentos(models.Model):
    _name = "descuentos.model"
    _description = "Descuentos"

    category_id=fields.Many2one('res.partner.category', string="Categoria del cliente",required=True) 
    f_product_id = fields.Many2one('fproduct.dofamily', string="Familia",required=True)    
    color=fields.Selection([('color 1','Color1'),('color2 2','Color 2'),('color 3','Color 3')], string="Color",required=True)
    min_descuento=fields.Float(string="Minimo descuento",required=True)
    max_descuento=fields.Float(string="Maximo descuento",required=True)
    fecha_inicio=fields.Date(string="Fecha Inicio",required=True)
    fecha_vencimiento=fields.Date(string="Fecha Vencimiento",required=True)

    @api.constrains('min_descuento', 'max_descuento','fecha_inicio','fecha_vencimiento')
    def _check_values(self):
        if self.min_descuento <= 0.0 or self.min_descuento>100:
            raise ValidationError(_('El valor del descuento mínimo no puede ser igual a cero o mayor que 100'))
        elif self.max_descuento <= self.min_descuento or self.max_descuento>100:
            raise ValidationError(_('El valor del descuento máximo no puede ser igual o menor que el descuento mínimo.'))
        elif str(self.fecha_inicio) < str(date.today()):
            raise ValidationError(_('La fecha de inicio no puede ser menor a la fecha actual'))
        elif self.fecha_vencimiento <=self.fecha_inicio:
            raise ValidationError(_('La fecha de vencimiento no puede ser menor o igual a la fecha de inicio'))

