from odoo import models, fields, api
from odoo.tools.translate import _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    display_user_id = fields.Many2one(
        'res.users', string="Assigned to", compute='_compute_display_user_id', store=True, readonly=False)

    @api.depends('res_id', 'res_model', 'display_user_id')
    def _compute_display_user_id(self):
        """
        Calcula y establece el campo 'display_user_id' en función del modelo y el ID de recurso.

        Si el modelo es 'res.partner', se obtiene directamente el user_id del res.partner.
        De lo contrario, se asume que existe una relación con res.partner y se obtiene el user_id del partner_id relacionado.
        Si no hay un display_user_id asignado, se muestra el usuario actual.
        """
        for activity in self:
            if not activity.display_user_id:
                display_user_id = self._get_display_user_id(
                    activity.res_model, activity.res_id)
                activity.display_user_id = display_user_id

    def _get_display_user_id(self, res_model, res_id):
        """
        Obtiene el user_id del recurso relacionado según el modelo y el ID de recurso.

        Si el modelo es 'res.partner', se obtiene directamente el user_id del res.partner.
        De lo contrario, se asume que existe una relación con res.partner y se obtiene el user_id del partner_id relacionado.
        Si no hay un display_user_id asignado, se devuelve el ID del usuario actual.
        """
        display_user_id = False
        if res_model == 'res.partner':
            partner = self.env['res.partner'].sudo().browse(res_id)
            display_user_id = partner.user_id.id
        else:
            related_partner = self.env[res_model].sudo().browse(
                res_id).partner_id
            if related_partner:
                display_user_id = related_partner.user_id.id

        if not display_user_id:
            display_user_id = self.env.user.id

        return display_user_id

    @api.model
    def create(self, vals):
        """
        Crea una nueva actividad.

        Si se proporciona un display_user_id, se establece como user_id en el registro creado.
        """
        display_user_id = vals.get('display_user_id')
        if display_user_id:
            vals['user_id'] = display_user_id
        return super(MailActivity, self).create(vals)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """
        Realiza una búsqueda de actividades con ciertos criterios.

        Si el usuario actual no tiene los permisos de venta adecuados,
        se agrega un filtro adicional para mostrar solo las actividades asignadas al usuario actual.
        """
        current_user = self.env.user
        if not current_user.has_group('sales_team.group_sale_manager') and not current_user.has_group('sales_team.group_sale_salesman_all_leads'):
            args.append(('user_id', '=', current_user.id))
        return super(MailActivity, self.sudo()).search(args, offset=offset, limit=limit, order=order, count=count)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    user_id = fields.Many2one('res.users', string="Salesperson")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Actualiza el campo user_id cuando se cambia el partner_id en un registro de oportunidad de venta.

        Si se selecciona un partner_id, se establece el user_id como el user_id del partner seleccionado.
        De lo contrario, se establece el user_id como el usuario actual.
        """
        if self.partner_id:
            self.user_id = self.partner_id.user_id
        else:
            self.user_id = self.env.user

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """
        Realiza una búsqueda de oportunidades de venta con ciertos criterios.

        Si el usuario actual no tiene los permisos de venta adecuados,
        se agrega un filtro adicional para mostrar solo las oportunidades de venta asignadas al usuario actual.
        """
        current_user = self.env.user
        if not current_user.has_group('sales_team.group_sale_manager') and not current_user.has_group('sales_team.group_sale_salesman_all_leads'):
            args.append(('user_id', '=', current_user.id))
        return super(CrmLead, self).search(args, offset=offset, limit=limit, order=order, count=count)
