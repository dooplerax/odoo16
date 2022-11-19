# -*- coding: utf-8 -*-

import os
import time
import logging

from jinja2 import Environment, FileSystemLoader

from odoo import models, api, fields
from odoo.exceptions import Warning as UserError

from . import utils
from ..xades.sri import DocumentXML
from ..xades.xades import Xades

TEMPLATES = {
    'out_invoice': 'out_invoice.xml'
}


class AccountWithdrawing(models.Model):
    _name = 'account.retention'
    _inherit = ['account.retention', 'account.edocument']
    _logger = logging.getLogger(_name)

    def get_secuencial(self):
        return getattr(self, 'name')[6:15]

    def _info_withdrawing(self, withdrawing):
        """
        """
        # generar infoTributaria
        company = withdrawing.company_id
        partner = withdrawing.invoice_id.partner_id
        obligadoContabilidad = 'SI'
        if company.partner_id.property_account_position_id.name == u'Persona natural no obligada a llevar contabilidad':
            obligadoContabilidad = 'NO'
        infoCompRetencion = {
            'fechaEmision': "{}/{}/{}".format(withdrawing.date.year, str(withdrawing.date.month).zfill(2), str(withdrawing.date.day).zfill(2)),
            'dirEstablecimiento': company.street,
            'obligadoContabilidad': obligadoContabilidad,
            'tipoIdentificacionSujetoRetenido': utils.tipoIdentificacion[partner.l10n_latam_identification_type_id.display_name],
            'razonSocialSujetoRetenido': partner.name,
            'identificacionSujetoRetenido': partner.vat,
            'periodoFiscal': str(withdrawing.date.year),
        }
        if company.company_registry and company.company_registry != 'NA':
            infoCompRetencion.update({'contribuyenteEspecial': company.company_registry})
        return infoCompRetencion

    def _impuestos(self, retention):
        """
        """

        def get_codigo_retencion(linea):
            if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat', 'ret_vat_srv']:
                return utils.tabla21[str(abs(int(line.tax_id.amount)))]
            elif line.tax_id.tax_group_id.l10n_ec_type in ['ret_ir']:
                code = line.tax_id.description
                return code
            else:
                return '8'

        impuestos = []
        for line in retention.move_ids:
            impuesto = {
                'codigo': utils.tabla20[line.tax_id.tax_group_id.l10n_ec_type],
                'codigoRetencion': get_codigo_retencion(line),
                'baseImponible': '%.2f' % (line.base),
                'porcentajeRetener': str(abs(line.tax_id.amount)),
                'valorRetenido': '%.2f' % (abs(line.amount)),
                'codDocSustento': retention.invoice_id.sustento_id.code,
                'numDocSustento': retention.invoice_id.l10n_latan_document_number,
                'fechaEmisionDocSustento': time.strftime('%d/%m/%Y',
                                                         time.strptime(retention.invoice_id.date, '%Y-%m-%d'))

            }
            
            totalImpuesto = {
                            'codigo': utils.tabla17[temp_tax.tax_group_id.l10n_ec_type],
                            'codigoPorcentaje': utils.tabla18[str(int(temp_tax.real_amount))],
                            'baseImponible': mov.tax_base_amount,
                            'tarifa': int(temp_tax.real_amount),
                            'valor': abs(mov.amount_currency)
                        }
            impuestos.append(impuesto)
        return {'impuestos': impuestos}

    def render_document(self, document, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ewithdrawing_tmpl = env.get_template('ewithdrawing.xml')
        data = {}
        data.update(self._info_tributaria(document, access_key, emission_code))
        data.update(self._info_withdrawing(document))
        data.update(self._impuestos(document))
        data.update({'direccionCliente': document.partner_id.contact_address})
        email = document.partner_id.email
        
        data.update({'emailCliente': email})
        edocument = ewithdrawing_tmpl.render(data)
        return edocument

    def render_authorized_document(self, autorizacion):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        edocument_tmpl = env.get_template('authorized_withdrawing.xml')
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion,
            'ambiente': autorizacion.ambiente,
            'fechaAutorizacion': str(autorizacion.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S")),
            'comprobante': autorizacion.comprobante
        }
        auth_withdrawing = edocument_tmpl.render(auth_xml)
        return auth_withdrawing

    pre_send_sri = fields.Boolean(default=False)

    
    def action_generate_document1(self):
        if self.authorization_sri == True:
            raise UserError(u'El documento ya fue enviado al SRI')
        if self.invoice_id.extracontable == True:
            raise UserError(u'Documento seleccionado como Extra Contable no puede ser enviado al SRI')

        self.authorization_sri = True
        

    
    def action_generate_document(self):

        if self.authorization_sri == True:
            raise UserError(u'El documento ya fue enviado al SRI')
        

        self.authorization_sri = True
        

        error_msg = ''
        # try:
        for obj in self:
            # self.check_date(obj.date)
            self.check_before_sent()
            if not obj.authorization_number:
                access_key, emission_code = self._get_codes('account.retention')
            else:
                access_key = obj.authorization_number
                emission_code = self.company_id.emission_code

            ewithdrawing = self.render_document(obj, access_key, emission_code)
            self._logger.debug(ewithdrawing)
            inv_xml = DocumentXML(ewithdrawing, 'withdrawing')
            inv_xml.validate_xml()
            # xades = Xades()
            # file_pk12 = obj.company_id.electronic_signature
            # password = obj.company_id.password_electronic_signature

            # xades_error, signed_document = xades.sign(ewithdrawing, file_pk12, password)
            # if xades_error:
            #     error_msg = signed_document
            #     raise UserError(error_msg)
            
            ok, estado, errores = inv_xml.send_receipt(signed_document, obj.company_id.env_service)
            obj.estado_autorizacion = estado

            if obj.company_id.env_service == '1':
                obj.ambiente = 'PRUEBAS'
            else:
                obj.ambiente = 'PRODUCCION'

            obj.authorization_number = access_key
            obj.claveacceso = access_key

            if not ok:
                error_msg = errores
                return False, errores
            else:
                obj.authorization_sri = True

            obj.authorization_sri = True
            attac = self.env['ir.attachment'].search([('res_name', '=', obj.name),
                                                        ('res_model', '=', 'account.retention'),
                                                        ('name', 'ilike', '.pdf'),
                                                        ('company_id', '=', obj.company_id.id)
                                                        ])

            # for at in attac:
            #     at.unlink()

            # return self.print_retention()

        # except Exception as e:
        #     if error_msg != '':
        #         return False, error_msg
        #     return False, e.message

    
    def retention_print(self):
        return self.env['report'].get_action(
            self,
            'l10n_ec_einvoice.report_eretention'
        )


# class AccountInvoice(models.Model):
#     _inherit = 'account.invoice'

    
#     def action_generate_eretention(self):
#         for obj in self:
#             if not obj.journal_id.auth_ret_id.is_electronic:
#                 return True
#             obj.retention_id.action_generate_document()

    
#     def action_retention_create(self):
#         super(AccountInvoice, self).action_retention_create()
#         for obj in self:
#             if obj.type in ['in_invoice', 'liq_purchase']:
#                 self.action_generate_eretention()
