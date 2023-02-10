from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

class ProductTelas(models.Model):
    _inherit= 'product.template'
    colorTela=fields.Many2one('product.color.catalogo',string="Colores")
    visilloTela=fields.Many2one('product.visillo.catalogo',string='Visillo')
    texturaTela=fields.Many2one('product.textura.catalogo',string='Textura')
    composicionTela=fields.Many2one('product.composicion.catalogo',string='Composicion')
    pesoTela=fields.Float(string='Peso')
    presentacionTela=fields.Many2one('product.presentacion.catalogo',string='Presentacion')
    anchorolloTela=fields.Float(string='Ancho de Rollo')
    anchofranjaTela=fields.Float(string='Ancho de franja')
    aperturaTela=fields.Float(string='Apertura')
    umrollo=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')
    umfranja=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')

class ProductPerfileria(models.Model):
    _inherit= 'product.template'
    colorPerfileria=fields.Many2one('product.color.catalogo',string="Colores")
    pestaniaPerfileria=fields.Many2one('product.pestania.catalogo',string="Pestañas")
    ranuraPerfileria=fields.Many2one('product.ranura.catalogo',string='Ranura')
    longitudPerfileria=fields.Float(string='Longitud')
    diametroPerfileria=fields.Float(string='Diametro')
    medidaRanuraPerfileria=fields.Float(string='Medida Ranura')
    umlongitud=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')
    umdiametro=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')


class ProductAccesorios(models.Model):
    _inherit= 'product.template'
    colorAccesorios=fields.Many2one('product.color.catalogo',string="Colores")
    mandoAccesorios=fields.Many2one('product.mando.catalogo',string="Mandos")
    logoAccesorios=fields.Many2one('product.logo.catalogo',string="Logos")
    diametroAccesorios=fields.Float(string='Diametro')
    umdiametroA=fields.Many2one('product.unidad.catalogo',string='Unidad de medida')


class CatalogoColores(models.Model):
    _name= 'product.color.catalogo'
    _description = 'Colores'
    _rec_name = 'colorTel'
    colorTel = fields.Char('Colores', required=True)
    _sql_constraints = [
        ('colorTel_uniq', 'unique (colorTel)', "Valor ya registrado, ingrese otro valor"),
    ]

    @api.onchange('colorTel')
    def set_caps(self):        
        if self.colorTel:
            self.colorTel=str(self.colorTel).upper()
        else:
            self.colorTel=''



class CatalogoVisillo(models.Model):
    _name= 'product.visillo.catalogo'
    _description = 'Visillo'
    _rec_name = 'visillo'
    visillo = fields.Char('Visillos', required=True)
    @api.onchange('visillo')
    def set_caps(self):        
        if self.visillo:
            self.visillo=str(self.visillo).upper()
        else:
            self.visillo=''

class CatalogoTextura(models.Model):
    _name= 'product.textura.catalogo'
    _description = 'Texturas'
    _rec_name = 'textura'
    textura = fields.Char('Texturas', required=True)
    @api.onchange('textura')
    def set_caps(self):        
        if self.textura:
            self.textura=str(self.textura).upper()
        else:
            self.textura=''

class CatalogoPresentacion(models.Model):
    _name= 'product.presentacion.catalogo'
    _description = 'Presentaciones'
    _rec_name = 'presentacion'
    presentacion = fields.Char('Presentaciones', required=True)
    @api.onchange('presentacion')
    def set_caps(self):        
        if self.presentacion:
            self.presentacion=str(self.presentacion).upper()
        else:
            self.presentacion=''

class CatalogoPestania(models.Model):
    _name= 'product.pestania.catalogo'
    _description = 'Pestañas'
    _rec_name = 'pestania'
    pestania = fields.Char('Pestañas', required=True)
    @api.onchange('pestania')
    def set_caps(self):        
        if self.pestania:
            self.pestania=str(self.pestania).upper()
        else:
            self.pestania=''

class CatalogoRanura(models.Model):
    _name= 'product.ranura.catalogo'
    _description = 'Ranuras'
    _rec_name = 'ranura'
    ranura = fields.Char('Ranuras', required=True)
    @api.onchange('ranura')
    def set_caps(self):        
        if self.ranura:
            self.ranura=str(self.ranura).upper()
        else:
            self.ranura=''

class CatalogoMando(models.Model):
    _name= 'product.mando.catalogo'
    _description = 'Mandos'
    _rec_name = 'mando'
    mando = fields.Char('Mandos', required=True)
    @api.onchange('mando')
    def set_caps(self):        
        if self.mando:
            self.mando=str(self.mando).upper()
        else:
            self.mando=''

class CatalogoLogo(models.Model):
    _name= 'product.logo.catalogo'
    _description = 'Logos'
    _rec_name = 'logo'
    logo = fields.Char('Logos', required=True)
    @api.onchange('logo')
    def set_caps(self):        
        if self.logo:
            self.logo=str(self.logo).upper()
        else:
            self.logo=''

class CatalogoComposicion(models.Model):
    _name= 'product.composicion.catalogo'
    _description = 'Composiciones'
    _rec_name = 'composicion'
    composicion = fields.Char('Composiciones', required=True)
    @api.onchange('composicion')
    def set_caps(self):        
        if self.composicion:
            self.composicion=str(self.composicion).upper()
        else:
            self.composicion=''

class CatalogoUnidadMedida(models.Model):
    _name= 'product.unidad.catalogo'
    _description = 'Unidades'
    _rec_name = 'unidad'
    unidad = fields.Char('Unidades', required=True)
    @api.onchange('unidad')
    def set_caps(self):        
        if self.unidad:
            self.unidad=str(self.unidad).upper()
        else:
            self.unidad=''