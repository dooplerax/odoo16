from odoo import api, fields, models, _

#from ec_models import *


class AddCatalogInProduct(models.Model):
    _inherit = 'product.template'


    class_inherit = fields.Many2one('cproduct.doclass', 'Clase de producto' )
    subclass_inherit = fields.Many2one('subproduct.dosubclass', 'Subclase de producto')
    fa_class_inherit = fields.Many2one('fproduct.dofamily', 'Familia de producto')
    mod_class_inherit = fields.Many2one('mproduct.domodel', 'Modelo de producto')
    sequence = fields.Integer("Secuencia", default=1)

    #@api.onchange('class_inherit')
    #def _onchange_sclass(self):
        #for record in self.class_inherit:
        #    if record.cl_name:
        #        return {'domain': {'subclass_inherit': [('subclass_inherit','=',1)]}}
        #contador = 0

    # counter_se = fields.Char("contador s", default=lambda self: _('New'))
    # codes = fields.Char('Code', default=lambda self: _('New'), track_visibility='onchange')

    @api.model
    def create(self, waltz):
        if waltz:
            waltz['codes'] = self.env['ir.sequence'].next_by_code('sprogroup.purchase.request') or _('New')

        return super(AddCatalogInProduct, self).create(waltz)

    @api.model_create_multi
    def create(self, vals_list):
        producto = super(AddCatalogInProduct, self).create(vals_list)
        sequense = producto._calculate_sequence()
        str_seq = str(sequense).zfill(4)
        code = str(
            f"{producto.class_inherit.cl_name_code}-{producto.subclass_inherit.scl_name_code}-{producto.fa_class_inherit.f_name_code}-{producto.mod_class_inherit.m_name_code}-{str_seq}")

        producto.write({'default_code': code, "sequence": sequense})

        return producto

    def _calculate_sequence(self):
        self.ensure_one()
        sql = """
            select max("sequence")  from product_template pt 
        """
        self.env.cr.execute(sql)
        value = self.env.cr.fetchone()
        return value[0] + 1 if value[0] else 1
