from odoo import fields, models,api,_
from odoo.exceptions import ValidationError
from datetime import date




class Descuentos(models.Model):
    _name = "descuentos.model"
    _description = "Descuentos"
    # class_inherit = fields.Many2one('cproduct.doclass', 'Clase de producto' )
    category_id=fields.Many2one('res.partner.category', string="Categoria del cliente",required=True) 
    fa_class_inherit = fields.Many2one('fproduct.dofamily', string="Familia",domain="[('scl_product_id.cl_product_id.cl_name','=','TELAS')]")
    min_descuento=fields.Float(string="Minimo descuento",required=True)
    max_descuento=fields.Float(string="Maximo descuento",required=True)
    fecha_inicio=fields.Date(string="Fecha Inicio",required=True)
    fecha_vencimiento=fields.Date(string="Fecha Vencimiento",required=True)
    active = fields.Boolean(string="Estado",default=True)
    color_id=fields.Many2one("product.template",domain="[('fa_class_inherit','=',fa_class_inherit)]")
    colores=fields.Many2one('product.color.catalogo')


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

    # @api.onchange('class_inherit')
    # def onchange_class_inherit(self):
    #     for rec in self:
    #         return {'domain':{'fa_class_inherit':[('class_inherit','=',rec.fa_class_inherit.id)]}}


