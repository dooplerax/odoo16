from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError

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
    classification = fields.Boolean('Clasificación', default=False)
    alternate_code = fields.Char(string="Código Alterno", required=True, copy=False)
    
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
        # Obtener el código guardado en la base de datos
        original_default_code = self._origin.default_code if self._origin else False

        # Si ya tiene un código personalizado de 5 dígitos, devolverlo
        if original_default_code and not self.classification and len(original_default_code) == 5:
            return original_default_code

        elif not self.classification:
            # Generar el número de secuencia de 5 dígitos sin considerar las clases relacionadas
            existing_codes = self.env['product.template'].search([
                ('classification', '=', False),
                # Buscar códigos de producto de 5 dígitos
                ('default_code', 'ilike', '_____')
            ], order='default_code')

            existing_numbers = []
            for code in existing_codes:
                if code.default_code.isdigit() and len(code.default_code) == 5:
                    existing_numbers.append(int(code.default_code))

            str_seq = '00001'
            while int(str_seq) in existing_numbers:
                str_seq = str(int(str_seq) + 1).zfill(5)

            return str_seq

        else:

            base_code = "{}-{}-{}-{}".format(
                self.class_inherit.cl_name_code,
                self.subclass_inherit.scl_name_code,
                self.fa_class_inherit.f_name_code or "000",
                self.mod_class_inherit.m_name_code
            )

            original_record = self._origin

            existing_codes = self.env['product.template'].search([
                ('default_code', 'ilike', '{}-%'.format(base_code)),
                # Excluir el registro original sin cambios
                ('id', '!=', original_record.id)
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

    @api.depends('class_inherit', 'subclass_inherit', 'fa_class_inherit', 'mod_class_inherit', 'classification')
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

    predefined_attribute_names = {
        'TELAS-ZEBRA': ['ANCHO DE ROLLO', 'ANCHO DE FRANJA', 'COLOR', 'VISILLO', 'TEXTURA', 'PESO', 'COMPOSICION'],
        'TELAS-SCREEN': ['ANCHO DE ROLLO', 'APERTURA', 'COLOR', 'TEXTURA', 'PESO', 'COMPOSICION'],
        'TELAS-BLACKOUT': ['ANCHO DE ROLLO', 'COLOR', 'TEXTURA', 'PESO', 'COMPOSICION'],
        'TELAS-TRASLUCIDAS': ['ANCHO DE ROLLO', 'COLOR', 'TEXTURA', 'COMPOSICION'],
    }

    @api.onchange('subclass_inherit', 'classification')
    def _onchange_subclass_inherit(self):
        if self.classification and self.subclass_inherit:
            class_inherit = self.subclass_inherit.cl_product_id

            # Ajustar los atributos y valores predeterminados para cada clase y subclase
            key = f"{class_inherit.cl_name}-{self.subclass_inherit.scl_name}"
            predefined_attribute_names = self.predefined_attribute_names.get(key, [
            ])

            # Clear existing attribute lines
            self.attribute_line_ids = [(5, 0, 0)]

            if predefined_attribute_names and class_inherit.cl_name and self.subclass_inherit.scl_name:
                attributes_to_add = self.env['product.attribute'].search([
                    ('name', 'in', predefined_attribute_names),
                    ('class_inherit.cl_name', '=', class_inherit.cl_name),
                    ('subclass_inherit.scl_name', '=',
                     self.subclass_inherit.scl_name),
                ])

                attribute_lines_to_add = [(0, 0, {
                    'attribute_id': attribute.id,
                }) for attribute in attributes_to_add]

                self.attribute_line_ids = attribute_lines_to_add

                    # Set the attribute_id_readonly field for existing attribute lines
                """ for line in self.attribute_line_ids:
                    line.attribute_id_readonly = True """

        else:
            # Handle the case when subclass_inherit is False or not set
            # You may want to take some action or clear the attribute lines here
            self.attribute_line_ids = [(5, 0, 0)]


class ProductAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    classification = fields.Boolean(related='product_tmpl_id.classification', readonly=True)
    predefined_attribute_names = {
        'TELAS-ZEBRA': ['ANCHO DE ROLLO', 'ANCHO DE FRANJA', 'COLOR', 'VISILLO', 'TEXTURA', 'PESO', 'COMPOSICION'],
        'TELAS-SCREEN': ['ANCHO DE ROLLO', 'APERTURA', 'COLOR', 'TEXTURA', 'PESO', 'COMPOSICION'],
        'TELAS-BLACKOUT': ['ANCHO DE ROLLO', 'COLOR', 'TEXTURA', 'PESO', 'COMPOSICION'],
        'TELAS-TRASLUCIDAS': ['ANCHO DE ROLLO', 'COLOR', 'TEXTURA', 'COMPOSICION'],
    }
    # medida = fields.Selection(related='attribute_id.medida', string='Unidad de Medida', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', related='attribute_id.product_uom_id', string='Unidad de Medida')

    """ def unlink(self):
        for attribute_line in self:
            if attribute_line.product_tmpl_id:
                key = f"{attribute_line.product_tmpl_id.class_inherit.cl_name}-{attribute_line.product_tmpl_id.subclass_inherit.scl_name}"
                predefined_attributes = self.predefined_attribute_names.get(key, [])
                if attribute_line.attribute_id.name in predefined_attributes:
                    raise exceptions.UserError(
                        "No se puede borrar un valor por defecto de atributos y variantes para esta clase y subclase.")
        return super(ProductAttributeLine, self).unlink() """

    attribute_id_readonly = fields.Boolean(store=False)

    """ def _compute_attribute_id_readonly(self):
        for line in self:
            line.attribute_id_readonly = line.product_tmpl_id.subclass_inherit """


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    """  @api.onchange('classification')
    def _onchange_classification(self): 
        if not self.classification:
            self.class_inherit.required = False
            self.subclass_inherit.required = False
            self.fa_class_inherit.required = False
            self.mod_class_inherit.required = False
        else:
            self.class_inherit.required = True
            self.subclass_inherit.required = True
            self.fa_class_inherit.required = True
            self.mod_class_inherit.required = True
            pass """
