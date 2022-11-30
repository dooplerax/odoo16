from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    electronic_signature = fields.Char(
        'Firma Electrónica',
        size=128,
    )

    password_electronic_signature = fields.Char(
        'Clave Firma Electrónica',
        size=255,
    )
    emission_code = fields.Selection([('1', 'Normal')], string='Tipo de Emisión',
                                     required=True, default='1')
    env_service = fields.Selection([('1', 'Pruebas'), ('2', 'Producción')], tring='Tipo de Ambiente',
                                   required=True, default='1'
                                   )
    
    document_sequense = fields.Integer('Secuencia de Documentos', default=1)
    
    
    