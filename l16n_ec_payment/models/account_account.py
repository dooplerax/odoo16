from odoo import models, fields, api
from odoo.exceptions import ValidationError

L10N_EC_TAXSUPPORTS = [
    ('01', '01 Crédito tributario para declaración de IVA (servicios y bienes distintos de inventarios y activos fijos)'),
    ('02', '02 Costo o gasto para declaración de IR (servicios y bienes distintos de inventarios y activos fijos)'),
    ('03', '03 Activo fijo - Crédito tributario para devolución de IVA'),
    ('04', '04 Activo fijo - Costo o gasto para declaración de IR'),
    ('05', '05 Liquidación de viáticos, hospedaje y alimentación - Gastos de IR (a nombre de empleados y no de la empresa)'),
    ('06', '06 Inventario - Crédito tributario para devolución de IVA'),
    ('07', '07 Inventario - Costo o gasto para declaración de IR'),
    ('08', '08 Monto pagado para solicitud de reembolso de gastos (intermediario)'),
    ('09', '09 Reembolso de reclamaciones'),
    ('10', '10 Distribución de dividendos, beneficios o utilidades'),
    ('15', '15 Pagos realizados por consumo propio y de terceros de servicios digitales'),
    ('00', '00 Casos especiales cuyo soporte no aplica a las opciones anteriores')
]

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_client_id = fields.Many2one(
        'account.account',
        string="Cuenta predeterminada a cobrar",
        config_parameter='accounting_settings.account_client_id'
    )
    account_provider_id = fields.Many2one(
        'account.account',
        string="Cuenta predeterminada a pagar",
        config_parameter='accounting_settings.account_provider_id'
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # _sql_constraints = [
    #     ('unique_vat', 'unique(vat)', 'El número de identificación ya está registrado.')
    # ]

    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
                                                  string="Account Payable",
                                                  domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                  help="This account will be used instead of the default one as the payable account for the current partner",
                                                  required=False)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
                                                     string="Account Receivable",
                                                     domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                     help="This account will be used instead of the default one as the receivable account for the current partner",
                                                     required=False)

    @api.model
    def create(self, vals):
        """ Asigna las cuentas por defecto de res.config.settings al crear un contacto """
        config = self.env['ir.config_parameter'].sudo()
        account_client_id = int(config.get_param('accounting_settings.account_client_id', default=0))
        account_provider_id = int(config.get_param('accounting_settings.account_provider_id', default=0))

        if account_client_id:
            vals['property_account_receivable_id'] = account_client_id

        if account_provider_id:
            vals['property_account_payable_id'] = account_provider_id

        return super(ResPartner, self).create(vals)

    @api.constrains('vat')
    def _check_unique_vat(self):
        """ Validación para evitar duplicados en el campo vat """
        if not self.env.context.get('skip_identification_constraint'):
            return
        for record in self:
            if record.vat:
                existing_partner = self.env['res.partner'].search([
                    ('vat', '=', record.vat),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_partner:
                    raise ValidationError('El número de identificación ya está registrado para otro contacto.')

class AccountMove(models.Model):
    _inherit = "account.move"

    taxsupport_code = fields.Selection(
        L10N_EC_TAXSUPPORTS,
        string="Sustento del comprobante",
        store=True, readonly=False,
        help="Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS",
        default='01',
    )

    @api.model
    def create(self, vals):
        move = super(AccountMove, self).create(vals)

        # Manejo seguro de fechas
        withhold_date = vals.get('l10n_ec_withhold_date')
        invoice_date = vals.get('invoice_date')

        if not move.date:
            if withhold_date:  # Primera prioridad: fecha de retención
                move.date = withhold_date
            elif invoice_date:  # Segunda prioridad: fecha de factura
                move.date = invoice_date

        if withhold_date:
            move.date = withhold_date

        return move
