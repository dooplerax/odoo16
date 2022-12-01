from odoo import api, fields, models, _

#from ec_models import *


class AddCatalogInProduct(models.Model):
    _inherit = 'product.template'


    class_inherit = fields.Many2one('cproduct.doclass', 'Clase de producto', required=True)
    subclass_inherit = fields.Many2one('subproduct.dosubclass', 'Subclase de producto', required=True)
    fa_class_inherit = fields.Many2one('fproduct.dofamily', 'Familia de producto', required=True)
    mod_class_inherit = fields.Many2one('mproduct.domodel', 'Modelo de producto', required=True)

    #@api.onchange('class_inherit')
    #def _onchange_sclass(self):
        #for record in self.class_inherit:
        #    if record.cl_name:
        #        return {'domain': {'subclass_inherit': [('subclass_inherit','=',1)]}}
        #contador = 0



    #counter_se = fields.Char("contador s", default=lambda self: _('New'))
    codes = fields.Char('Code', default=lambda self: _('New'), track_visibility='onchange')

    @api.model
    def create(self, waltz):
        if waltz:
            waltz['codes'] = self.env['ir.sequence'].next_by_code('sprogroup.purchase.request') or _('New')

        return super(AddCatalogInProduct, self).create(waltz)

    @api.model_create_multi
    def create(self, vals_list):

        producto = super(AddCatalogInProduct, self).create(vals_list)

        code = str(f"{producto.class_inherit.cl_name_code}-{producto.subclass_inherit.scl_name_code}-{producto.fa_class_inherit.f_name_code}-{producto.mod_class_inherit.m_name_code}-000{self.codes}")

        producto.write({'default_code': code})

        return producto


