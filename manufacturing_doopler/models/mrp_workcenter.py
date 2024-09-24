from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    responsible = fields.Many2one('res.partner',string="Responsible")