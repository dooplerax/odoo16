from odoo import models, fields, api
from odoo.tools.translate import _



class AccountMove(models.Model):
    _inherit = 'account.move'

    opportunity_id = fields.Many2one('crm.lead', string='Opportunity')


class MailActivity(models.Model):
    _inherit = 'mail.activity'


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
        display_user_id = False
        if res_model == 'res.partner':
            partner = self.env['res.partner'].browse(res_id)
            display_user_id = partner.user_id.id
        elif res_model == 'account.move' or res_model == 'sale.order':
            related_partner = self.env[res_model].browse(res_id).partner_id
            if related_partner:
                display_user_id = related_partner.user_id.id
        elif res_model == 'crm.lead':
            lead = self.env['crm.lead'].browse(res_id)
            if lead:
                display_user_id = lead.user_id.id
        if not display_user_id:
            display_user_id = self.env.user.id
        return display_user_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Obtener el ID del modelo del diccionario 'vals'
            res_model_id = vals.get('res_model_id')
            model_obj = self.env['ir.model']
            display_user_id = vals.get('display_user_id', False)
            if display_user_id:
                vals['user_id'] = display_user_id
            res_model = model_obj.sudo().search(
                [('id', '=', res_model_id)], limit=1).model if res_model_id else False


            """  if res_model == 'sale.order':
                activity = super(MailActivity, self).create(vals)
                res_id = vals.get('res_id')
                if res_id and display_user_id:
                    sale_order = self.env['sale.order'].browse(res_id)
                    activity.user_id = display_user_id
                    if sale_order.partner_id:
                        lead_vals = {
                            'name': "",
                            'user_id': vals.get('display_user_id', sale_order.partner_id.user_id.id),
                            'partner_id': sale_order.partner_id.id,
                            'type': 'opportunity',
                            'stage_id': False,
                            'expected_revenue': False,
                            'recurring_revenue': False,
                            'recurring_revenue_monthly': False,
                        }
                        lead = self.env['crm.lead'].create(lead_vals)
                        vals['res_model_id'] = self.env.ref(
                            'crm.model_crm_lead').id
                        vals['res_id'] = lead.id
                        activity = super(MailActivity, self).create(vals)

                return activity """
            if res_model == 'res.partner':
                print(vals)

                res_id = vals.get('res_id')
                activity = super(MailActivity, self).create(vals)
                if res_id:
                    lead_vals = {
                        'name': "",
                        'user_id': display_user_id,
                        'partner_id': res_id,
                        'type': 'opportunity',
                        'stage_id': False,
                        'expected_revenue': False,
                        'recurring_revenue': False,
                        'recurring_revenue_monthly': False,
                    }
                    lead = self.env['crm.lead'].create(lead_vals)
                    vals['res_model_id'] = 644
                    vals['res_id'] = lead.id
                    activity = super(MailActivity, self).create(vals)
                return activity
            else:
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
        return super(MailActivity, self).search(args, offset=offset, limit=limit, order=order, count=count)

    def action_create_calendar_event(self):
        action = super(MailActivity,self).action_create_calendar_event()
        opportunity = self.calendar_event_id.opportunity_id

        if opportunity and opportunity.partner_id.user_id:
            user_id = opportunity.partner_id.user_id.id
            action['context']['default_user_id'] = user_id
        return action

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

        """elif res_model == 'account.move' and display_user_id:
            activity = super(MailActivity, self).create(vals)
            res_id = vals.get('res_id')
            if res_id:
                account_move = self.env['account.move'].browse(res_id)
                if account_move:
                    lead_vals = {
                        'name': "",
                        'user_id': vals.get('display_user_id', account_move.partner_id.user_id.id),
                        'partner_id': account_move.partner_id.id,
                        'type': 'opportunity',
                        'stage_id': False,
                        'expected_revenue': False,
                        'recurring_revenue': False,
                        'recurring_revenue_monthly': False,
                    }
                    lead = self.env['crm.lead'].create(lead_vals)
                    vals['res_model_id'] = self.env['ir.model'].search(
                        [('model', '=', 'crm.lead')], limit=1).id
                    vals['res_id'] = lead.id
                    activity = super(MailActivity, self).create(vals)
            return activity """
