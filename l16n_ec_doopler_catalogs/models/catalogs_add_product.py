from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _

# from ec_models import *


class AddCatalogInProduct(models.Model):
    _inherit = 'product.template'

    class_inherit = fields.Many2one('cproduct.doclass', 'Clase de producto')
    subclass_inherit = fields.Many2one(
        'subproduct.dosubclass', 'Subclase de producto')
    fa_class_inherit = fields.Many2one(
        'fproduct.dofamily', 'Familia de producto')
    mod_class_inherit = fields.Many2one(
        'mproduct.domodel', 'Modelo de producto')
    details_ok = fields.Boolean('Detalles', default=False)
    m2 = fields.Float(string='m2', compute='_compute_m2', store=True)
    default_code = fields.Char(string='Internal Reference', required=True, copy=False,
                               readonly=True, default=lambda self: _('New'))

    @api.depends('anchorolloTela')
    def _compute_m2(self):
        """
        Calcula el valor del campo 'm2' basado en el campo 'anchorolloTela'.
        """
        for record in self:
            record.m2 = record.anchorolloTela * record.anchorolloTela

    # @api.onchange('class_inherit')
    # def _onchange_sclass(self):
        # for record in self.class_inherit:
        #    if record.cl_name:
        #        return {'domain': {'subclass_inherit': [('subclass_inherit','=',1)]}}
        # contador = 0

    # counter_se = fields.Char("contador s", default=lambda self: _('New'))
    # codes = fields.Char('Code', default=lambda self: _('New'), track_visibility='onchange')

    @api.onchange('class_inherit')
    def change_class_inehrit(self):
        """
        Evento que se dispara cuando cambia la clase heredada.

        Reinicia los valores de las clases relacionadas y actualiza el código por defecto.
        """
        self.subclass_inherit = False
        self.fa_class_inherit = False
        self.mod_class_inherit = False

    @api.onchange('subclass_inherit')
    def change_subclass_inherit(self):
        """
        Evento que se dispara cuando cambia la subclase heredada.

        Reinicia los valores de las clases relacionadas y actualiza el código por defecto.
        """
        self.fa_class_inherit = False
        self.mod_class_inherit = False

    @api.onchange('fa_class_inherit')
    def change_fa_class_inherit(self):
        """
        Evento que se dispara cuando cambia la familia heredada.

        Reinicia los valores de las clases relacionadas y actualiza el código por defecto.
        """
        self.mod_class_inherit = False

    @api.onchange('mod_class_inherit')
    def change_mod_class_inherit(self):
        """
        Evento que se dispara cuando cambia el modelo heredado.

        Actualiza el código por defecto.
        """

    @api.model
    def _generate_product_code(self):
        """
        Genera el código de producto en función de las clases relacionadas y el número de secuencia.

        :return: El código de producto generado.
        """
        self.ensure_one()  # Asegurarse de que solo se procesa un registro a la vez

        base_code = "{}-{}-{}-{}".format(
            self.class_inherit.cl_name_code,
            self.subclass_inherit.scl_name_code,
            self.fa_class_inherit.f_name_code or "000",
            self.mod_class_inherit.m_name_code
        )

        original_record = self._origin

        existing_codes = self.env['product.template'].search([
            ('default_code', 'ilike', '{}-%'.format(base_code)),
            ('id', '!=', original_record.id)  # Excluir el registro original sin cambios
        ], order='default_code')

        existing_numbers = []
        for code in existing_codes:
            parts = code.default_code.split('-')
            if len(parts) >= 2 and parts[-1].isdigit():
                existing_numbers.append(int(parts[-1]))

        str_seq = '0001'
        while int(str_seq) in existing_numbers:
            str_seq = str(int(str_seq) + 1).zfill(4)

        code = "{}-{}".format(base_code, str_seq)
        return code

    @api.depends('class_inherit', 'subclass_inherit', 'fa_class_inherit', 'mod_class_inherit')
    def _compute_default_code(self):
        for record in self:
            record.default_code = record._generate_product_code()

    @api.constrains('default_code')
    def _check_unique_default_code(self):
        """
        Valida que el código por defecto sea único en los productos existentes.

        :raises: ValidationError si el código por defecto ya existe en otro producto.
        """
        for record in self:
            if self.search([('default_code', '=', record.default_code), ('id', '!=', record.id)]):
                raise ValidationError(
                    'Un producto con esa Referencia Interna ya existe.')
