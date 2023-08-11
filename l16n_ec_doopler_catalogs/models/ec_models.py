# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.exceptions import AccessError


# class l16n_ec_doopler_catalogs(models.Model):
#     _name = 'l16n_ec_doopler_catalogs.l16n_ec_doopler_catalogs'
#     _description = 'l16n_ec_doopler_catalogs.l16n_ec_doopler_catalogs'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class DoClassCatalog(models.Model):
    _name = 'cproduct.doclass'
    _description = 'Class Product Doopler'
    _rec_name = 'cl_name'

    c_id = fields.Many2one('cproduct.doclass')
    cl_name = fields.Char('Clases de productos', required=True)
    cl_name_code = fields.Char('Código de clase', required=True, size=4)
    _sql_constraints = [
        ('cl_name_code_uniq', 'unique (cl_name_code)', "Código ya registrado!"),
    ]

    # Relaciones entre tablas subclase
    scl_product_ids = fields.One2many(
        'subproduct.dosubclass', 'cl_product_id', string='Subclases')

    @api.onchange('cl_name', 'cl_name_code')
    def convert_to_uppercase(self):
        if self.cl_name_code:
            self.cl_name_code = self.cl_name_code.upper()
        if self.cl_name:
            self.cl_name = self.cl_name.upper()

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError("No tiene permisos para crear un catálogo.")

        # Verificar si ya existe una clase con el mismo nombre
        existing_class = self.env['cproduct.doclass'].search(
            [('cl_name', '=', vals.get('cl_name'))])
        if existing_class:
            raise ValidationError(
                f"La clase '{vals.get('cl_name')}' ya ha sido creada.")

        # Establecer valores predeterminados para la nueva clase
        if not vals.get('cl_name_code'):
            vals['cl_name_code'] = 'TELA'
        return super(DoClassCatalog, self).create(vals)

    def write(self, vals):
        """ if self.cl_name.upper() in ['TELAS', 'ACCESORIOS', 'PERFILERIA', 'INSUMOS']:
            raise AccessError(
                "No tiene permisos para editar clases predeterminadas.") """
        return super(DoClassCatalog, self).write(vals)

    def unlink(self):
        default_class = self.env['cproduct.doclass'].search(
            [('cl_name', '=', 'TELAS')])
        protected_classes = ['TELAS', 'ACCESORIOS', 'PERFILERIA', 'INSUMOS']
        
        if default_class and self.cl_name.upper() in protected_classes:
            raise AccessError(
                "No tiene permisos para eliminar clases predeterminadas.")
        return super(DoClassCatalog, self).unlink()

    @api.ondelete(at_uninstall=False)
    def check_del_class(self):
        for clpro in self:
            if clpro.scl_product_ids:
                raise ValidationError(
                    _("No se puede eliminar debido que forma parte de otro catálogo o producto"))

    @api.constrains('cl_name_code')
    def check_cl_name_code(self):
        for record in self:
            if len(record.cl_name_code) != 4:
                raise ValidationError(
                    "El código de clase debe tener exactamente 4 letras/dígitos.")


class DoSubClassCatalog(models.Model):
    _name = 'subproduct.dosubclass'
    _description = 'Sub Class Product Doopler'
    _rec_name = 'scl_name'

    scl_name = fields.Char('Subclase de producto', required=True)
    scl_name_code = fields.Char('Código de subclase', required=True, size=4)

    # apunta a clase
    cl_product_id = fields.Many2one('cproduct.doclass', string="Clase")

    # Relacion entre tablas Family
    f_product_ids = fields.One2many(
        'fproduct.dofamily', 'scl_product_id', string='Subclases')

    _sql_constraints = [
        ('scl_name_code_uniq', 'unique (scl_name_code)', "Código ya registrado!"),
    ]

    @api.onchange('scl_name', 'scl_name_code')
    def convert_to_uppercase(self):
        if self.scl_name:
            self.scl_name = self.scl_name.upper()
        if self.scl_name_code:
            self.scl_name_code = self.scl_name_code.upper()

    @api.ondelete(at_uninstall=False)
    def check_del_class(self):
        for sclpro in self:
            if sclpro.f_product_ids:
                raise ValidationError(
                    _("No se puede eliminar debido que forma parte de otro catálogo o producto"))

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError("No tiene permisos para crear un catálogo.")
        return super(DoSubClassCatalog, self).create(vals)

    @api.constrains('scl_name_code')
    def check_scl_name_code(self):
        for record in self:
            if len(record.scl_name_code) != 4:
                raise ValidationError(
                    "El código de subclase debe tener exactamente 4 letras/dígitos.")


class DoFamilyCatalog(models.Model):
    _name = 'fproduct.dofamily'
    _description = 'Family Product Doopler'
    _rec_name = 'f_name'

    f_name = fields.Char('Familia de producto', required=True)
    f_name_code = fields.Char('Código de familia', required=True, size=4)

    # Relacion entre tabla modelo
    # m_product_ids = fields.One2many('mproduct.domodel', 'm_product_id', string='Family')

    # apunta a subclase
    scl_product_id = fields.Many2one('subproduct.dosubclass', "Subclase")
    _sql_constraints = [
        ('f_name_code_uniq', 'unique (f_name_code)', "Código ya registrado!"),
    ]

    @api.onchange('f_name', 'f_name_code')
    def convert_to_uppercase(self):
        if self.f_name:
            self.f_name = self.f_name.upper()
        if self.f_name_code:
            self.f_name_code = self.f_name_code.upper()

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError("No tiene permisos para crear un catálogo.")
        return super(DoFamilyCatalog, self).create(vals)

    @api.constrains('f_name_code')
    def check_f_name_code(self):
        for record in self:
            if len(record.f_name_code) != 4:
                raise ValidationError(
                    "El código de familia debe tener exactamente 4 letras/dígitos.")


class DoModelCatalog(models.Model):
    _name = 'mproduct.domodel'
    _description = 'Model Product Doopler'
    _rec_name = 'm_name'

    m_name = fields.Char('Modelo de producto', required=True)
    m_name_code = fields.Char(
        'Código de Modelo', required=True, size=3)

    # Apunta a Familia
    f_product_id = fields.Many2one('fproduct.dofamily', string="Familia")

    _sql_constraints = [
        ('f_mproduct_name_code_uniq', 'unique (m_name_code)', "Código ya registrado!"),
    ]

    @api.onchange('m_name', 'm_name_code')
    def convert_to_uppercase(self):
        if self.m_name:
            self.m_name = self.m_name.upper()
        if self.m_name_code:
            self.m_name_code = self.m_name_code.upper()

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError("No tiene permisos para crear un catálogo.")
        return super(DoModelCatalog, self).create(vals)

    @api.constrains('m_name_code')
    def check_m_name_code(self):
        for record in self:
            if len(record.m_name_code) != 3:
                raise ValidationError(
                    "El código de modelo debe tener exactamente 3 letras/dígitos.")
