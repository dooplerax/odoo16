from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools.misc import formatLang

class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_id = fields.Many2one('res.users', string='Salesperson')

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    display_user_id = fields.Many2one('res.users', string=_("Assigned to"), compute='_compute_display_user_id', store=True, readonly=False)
    assigned_user_id = fields.Many2one('res.users', string=_("Assigned to")) # Nuevo campo Many2one para almacenar al usuario asignado a la actividad
    user_id = fields.Many2one('res.users', string='Salesperson')
    
    @api.depends('res_id', 'res_model')
    def _compute_display_user_id(self):
        for activity in self:
            if activity.res_id and activity.res_model == 'res.partner':
                partner = self.env['res.partner'].browse(activity.res_id)
                activity.display_user_id = partner.user_id or self.env.user
            elif activity.res_id and activity.res_model == 'crm.lead':
                lead = self.env['crm.lead'].browse(activity.res_id)
                activity.display_user_id = lead.partner_id.user_id or self.env.user
            else:
                activity.display_user_id = self.env.user

    @api.model
    def create(self, vals):
        res_model_id = vals.get('res_model_id')
        res_model = self.env['ir.model'].sudo().browse(res_model_id)
        res_model = res_model.model if res_model else False
        vals['user_id'] = vals.get('display_user_id', False)
        if res_model == 'crm.lead' and not vals.get('res_id'):
            return super(MailActivity, self).create(vals)
        res_id = vals.get('res_id')

        if not vals['user_id']:
            if res_model == 'res.partner':
                partner = self.env['res.partner'].browse(res_id)
                vals['user_id'] = lead.partner_id.user_id.id if lead.partner_id and lead.partner_id.user_id else self.env.user.id
            elif res_model == 'crm.lead':
                lead = self.env['crm.lead'].browse(res_id)
                vals['user_id'] = lead.partner_id.user_id.id if lead.partner_id and lead.partner_id.user_id else self.env.user.id
                if lead:
                    return super(MailActivity, self).create(vals)

        if res_id and res_model == 'res.partner':
            activity = super(MailActivity, self).create(vals)
            partner_id = res_id
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                if partner:
                    #stage_name = 'Nuevo'
                    #stage = self.env['crm.stage'].search([('name', 'ilike', stage_name)], limit=1)
                    lead_vals = {
                        'name': " ",
                        'user_id': vals.get('display_user_id', partner.user_id.id),
                        'partner_id': partner_id,
                        # esto es para cargar cada actividad en clientes como una oportunidad
                        #'type': 'opportunity',
                        #'stage_id': False,
                        'expected_revenue': False,
                        'recurring_revenue': False,
                        'recurring_revenue_monthly': False,
                    }

                    lead = self.env['crm.lead'].create(lead_vals)
                    vals['res_model_id'] = self.env['ir.model'].sudo().search([('model', '=', 'crm.lead')], limit=1).id
                    vals['res_id'] = lead.id
                    activity = super(MailActivity, self).create(vals)
        else:
            activity = super(MailActivity, self).create(vals)
        return activity

    def write(self, vals):
            res = super().write(vals)
            display_user_id = vals.get('display_user_id')
            if display_user_id:
                self.display_user_id = display_user_id
            return res

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        current_user = self.env.user
        if not current_user.has_group('sales_team.group_sale_manager') and not current_user.has_group('sales_team.group_sale_salesman_all_leads'):
            args.append(('user_id', '=', current_user.id))
        return super(MailActivity, self.sudo()).search(args, offset=offset, limit=limit, order=order, count=count)

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.user_id = self.partner_id.user_id
        else:
            self.user_id = self.env.user
    display_user_id = fields.Many2one('res.users', string=_("Assigned to"), compute='_compute_display_user_id', store=True, readonly=False)

    @api.depends('user_id')
    def _compute_display_user_id(self):
        for lead in self:
            lead.display_user_id = lead.user_id

    @api.model
    def update_display_user_id(self, activity_vals):
        display_user_id = activity_vals.get('display_user_id')
        if display_user_id:
            lead_id = activity_vals.get('res_id')
            res_model = activity_vals.get('res_model')
            if res_model == 'crm.lead':
                lead = self.env['crm.lead'].search([('id', '=', lead_id)], limit=1)
                if lead:
                    lead.write({'display_user_id': display_user_id})
            elif res_model == 'res.partner':
                partner = self.env['res.partner'].search([('id', '=', lead_id)], limit=1)
                if partner:
                    partner.write({'user_id': display_user_id})

    @api.model
    def create(self, vals):
        lead = super(CRMLead, self).create(vals)
        self.update_display_user_id(vals)
        return lead

    def write(self, vals):
        res = super(CRMLead, self).write(vals)
        self.update_display_user_id(vals)
        return res

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        current_user = self.env.user
        if not current_user.has_group('sales_team.group_sale_manager') and not current_user.has_group('sales_team.group_sale_salesman_all_leads'):
            args.append(('user_id', '=', current_user.id))
        return super(CRMLead, self).search(args, offset=offset, limit=limit, order=order, count=count)