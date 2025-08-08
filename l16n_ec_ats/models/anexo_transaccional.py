# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import calendar
import os
import time

from jinja2 import Environment, FileSystemLoader

from odoo import fields, models
from odoo.exceptions import ValidationError


def get_years():
    year_list = []
    for i in range(int(time.strftime("%Y")) - 5, int(time.strftime("%Y")) + 2):
        year_list.append((str(i), str(i)))
    return year_list


class AnexoTransac(models.Model):
    _name = "l16n.reporte.trans"
    _description = 'Descripción'

    fact_manual = fields.Boolean('Facturación Manual', default=False)
    month = fields.Selection(
        [
            ('1', u'Enero'),
            ('2', u'Febrero'),
            ('3', u'Marzo'),
            ('4', u'Abril'),
            ('5', u'Mayo'),
            ('6', u'Junio'),
            ('7', u'Julio'),
            ('8', u'Agosto'),
            ('9', u'Septiembre'),
            ('10', u'Octubre'),
            ('11', u'Noviembre'),
            ('12', u'Diciembre')
        ],
        string='Mes',
        default='1'
    )
    year = fields.Selection(get_years(), string='Año')
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id.id  # noqa
    )
    txt_filename = fields.Char()
    txt_binary = fields.Binary()

    TEMPLATES = {'anexo_transaccional': 'anexo_transaccional.xml'}
    TIPO_IDENTIFICACION_GENERAL = {'Pasaporte': 'P', 'Cédula': 'C', 'RUC': 'R', 'Cédula Extranjera': 'P'}
    TIPO_IDENTIFICACION = {'Pasaporte': '03', 'Cédula': '02', 'RUC': '01', 'Cédula Extranjera': '03'}
    TP_ID_CLIENTE = {'Pasaporte': '06', 'Cédula': '05', 'RUC': '04', 'Cédula Extranjera': '06'}
    CARACTERES_PERRMITIDOS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 '

    @staticmethod
    def formato_fecha(par):
        fecha = "%s/%s/%s" % (str(par.day).zfill(2), str(par.month).zfill(2), par.year)
        return fecha

    def _lista_notas_credito(self, date_month_start, date_month_end):
        list_notas = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.user.company_id.id),
            ('invoice_date', '>=', date_month_start),
            ('invoice_date', '<=', date_month_end),
            ('move_type', 'in', ['out_refund'])
        ])
        resul_notas = {}
        total = 0
        for notas in list_notas:
            total += notas['amount_untaxed']
            base_exempt_vat, base_zero_vat, base_vats, base_ice = self._get_vat_values(notas)
            try:
                resul_notas[notas.partner_id.id]['baseImpGrav'] = str(
                    "{0:.2f}".format(
                        abs(float(resul_notas[notas.partner_id.id]['baseImpGrav'])) + abs(float(base_zero_vat))
                    )
                )
                resul_notas[notas.partner_id.id]['baseImpGrav'] = str(
                    "{0:.2f}".format(
                        abs(float(resul_notas[notas.partner_id.id]['baseImpGrav'])) + abs(float(base_vats))
                    )
                )
                resul_notas[notas.partner_id.id]['montoIce'] = str(
                    "{0:.2f}".format(float(resul_notas[notas.partner_id.id]['montoIce']) + base_ice)
                )
                resul_notas[notas.partner_id.id]['montoIva'] = str(
                    "{0:.2f}".format(abs(float(resul_notas[notas.partner_id.id]['montoIva'])) + abs(notas.amount_tax))
                )
                valorIva = float(resul_notas[notas.partner_id.id]['valorRetIva'])
                retRent = float(resul_notas[notas.partner_id.id]['valorRetRenta'])
                if notas.retention_id:
                    if notas.retention_id.state == 'done':
                        for impu in notas.retention_id.tax_ids:
                            if impu.tax_id.tax_group_id.code == 'ret_ir':
                                retRent += abs(impu.amount)
                            if impu.tax_id.tax_group_id.code in ['ret_vat_srv', 'ret_vat_b']:
                                valorIva += abs(impu.amount)
                resul_notas[notas.partner_id.id]['numeroComprobantes'] += 1
                resul_notas[notas.partner_id.id]['valorRetIva'] = str("{0:.2f}".format(valorIva))
                resul_notas[notas.partner_id.id]['valorRetRenta'] = str("{0:.2f}".format(retRent))
            except Exception:
                resul_notas[notas.partner_id.id] = {}
                resul_notas[notas.partner_id.id].update({
                    'tpIdCliente': str(self.TP_ID_CLIENTE[notas.partner_id.l10n_latam_identification_type_id.name])
                })
                resul_notas[notas.partner_id.id].update({'idCliente': str(notas.partner_id.vat)})
                resul_notas[notas.partner_id.id].update({'parteRelVtas': 'NO'})
                resul_notas[notas.partner_id.id].update({
                    'tipoComprobante': str(notas.l10n_latam_document_type_id.code)
                })
                if self.env.user.company_id.type_invoice == '1':
                    resul_notas[notas.partner_id.id].update({'tipoEmision': 'E'})
                else:
                    resul_notas[notas.partner_id.id].update({'tipoEmision': 'F'})
                resul_notas[notas.partner_id.id].update({'numeroComprobantes': 1})
                resul_notas[notas.partner_id.id].update({'baseNoGraIva': str("{0:.2f}".format(base_exempt_vat))})
                resul_notas[notas.partner_id.id].update({
                    'baseImponible': str("{0:.2f}".format(abs(base_zero_vat)))
                    if int(base_exempt_vat) == 0 else "0.00"
                })
                resul_notas[notas.partner_id.id].update({'baseImpGrav': str("{0:.2f}".format(abs(base_vats)))})
                resul_notas[notas.partner_id.id].update({'montoIce': str("{0:.2f}".format(base_ice))})
                resul_notas[notas.partner_id.id].update({'montoIva': str("{0:.2f}".format(abs(notas.amount_tax)))})
                valorIva = 0.0
                retRent = 0.0
                if notas.retention_id:
                    if notas.retention_id.state == 'done':
                        for impu in notas.retention_id.tax_ids:
                            if impu.tax_id.tax_group_id.code == 'ret_ir':
                                retRent += abs(impu.amount)
                            if impu.tax_id.tax_group_id.code in ['ret_vat_srv', 'ret_vat_b']:
                                valorIva += abs(impu.amount)
                resul_notas[notas.partner_id.id]['valorRetIva'] = str("{0:.2f}".format(valorIva))
                resul_notas[notas.partner_id.id]['valorRetRenta'] = str("{0:.2f}".format(retRent))
        return total, resul_notas

    def lista_compras(self, date_month_start, date_month_end):
        list_compras = []
        compras = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.user.company_id.id),
            ('invoice_date', '>=', date_month_start),
            ('invoice_date', '<=', date_month_end),
            ('move_type', 'in', ['in_invoice', 'liq_purchase', 'in_refund'])
        ])
        for comp in compras:
            temp = {}
            temp.update({'codSustento': str(comp.taxsupport_code)})
            temp.update({
                'tpIdProv': str(self.TIPO_IDENTIFICACION[comp.partner_id.l10n_latam_identification_type_id.name])
            })
            temp.update({'idProv': str(comp.partner_id.vat)})
            parte_rel = 'SI' if comp.commercial_partner_id.l10n_ec_related_party else 'NO'
            temp.update({'parteRel': str(parte_rel)})
            temp.update({'tipoComprobante': str(comp.l10n_latam_document_type_id.code)})
            temp.update({'tipoProv': False})
            if self.TIPO_IDENTIFICACION[comp.partner_id.l10n_latam_identification_type_id.name] == '03':
                tipo_prov = '01'
                if comp.partner_id.company_type == 'company':
                    tipo_prov = '02'
                temp.update({'tipoProv': tipo_prov})
                temp.update({'denoProv':  self.update_razon_social(comp.partner_id.name)})
            temp.update({'fechaRegistro': self.formato_fecha(comp.invoice_date)})
            temp.update({'establecimiento': str(comp.l10n_latam_document_number[0:3])})
            temp.update({'puntoEmision': str(comp.l10n_latam_document_number[4:7])})
            temp.update({'secuencial': str(comp.l10n_latam_document_number[8:17])})
            temp.update({'fechaEmision': str(self.formato_fecha(comp.invoice_date))})
            if comp.move_type == 'liq_purchase':
                if not comp.l10n_ec_authorization_number:
                    raise ValidationError(
                        u'El documento de liquidacion de compra '
                        + comp.l10n_latam_document_number
                        + u' no tiene clave de acceso'
                    )
                temp.update({'autorizacion': str(comp.l10n_ec_authorization_number)})
            else:
                if not comp.l10n_ec_authorization_number:
                    raise ValidationError(
                        "La factura de compra {} no tiene clave de acceso".format(comp.l10n_latam_document_number)
                    )
                temp.update({'autorizacion': str(comp.l10n_ec_authorization_number)})
            base_exempt_vat, base_zero_vat, base_vats, base_ice = self._get_vat_values(comp)
            temp.update({'baseNoGraIva': f'{base_exempt_vat:.2f}'})
            temp.update({
                'baseImponible': str(
                    "{0:.2f}".format(abs(base_zero_vat))
                ) if int(base_exempt_vat) == 0 else "0.00"
            })
            if comp.move_type == 'in_refund':
                amount_vat = abs(base_vats)
                amount_tax = abs(comp.amount_tax)
            else:
                amount_vat = base_vats
                amount_tax = comp.amount_tax
            temp.update({'baseImpGrav': str("{0:.2f}".format(amount_vat))})
            temp.update({'baseImpExe': '0.00'})
            temp.update({'montoIce': str("{0:.2f}".format(base_ice))})
            temp.update({'montoIva': str("{0:.2f}".format(amount_tax))})
            if comp.move_type == 'in_refund':
                doc_origen = comp.l16n_ec_invoice_origin_id
                if doc_origen:
                    temp.update({'estabModificado': str(doc_origen.l10n_latam_document_number[0:3])})
                    temp.update({'ptoEmiModificado': str(doc_origen.l10n_latam_document_number[4:7])})
                    temp.update({'secModificado': str(comp.l10n_latam_document_number[8:17])})
                    if not doc_origen.l10n_ec_authorization_number:
                        raise ValidationError(
                            u'El documento de nota de crédito {} no tiene clave de acceso'.format(comp.invoice_number)
                        )
                    temp.update({'autModificado': str(doc_origen.l10n_ec_authorization_number)})
                else:
                    raise ValidationError(u'Nota de crédito {} , no tiene documento que la sustente'.format(comp.name))
                pass
            tot_bases_imp_reemb = 0
            if comp.amount_total >= 500:
                fpago = 'VALIDAR FACTURA'
                if comp.l10n_ec_sri_payment_id:
                    fpago = comp.l10n_ec_sri_payment_id.code
                temp.update({'formaPago': fpago})
            if comp.l10n_ec_sri_payment_id.code == '08':
                tot_bases_imp_reemb = base_zero_vat
            temp.update({'totbasesImpReemb': str("{0:.2f}".format(tot_bases_imp_reemb))})
            valor_ret_bienes = 0
            ret_bienes10 = 0
            val_ret_serv20 = 0
            val_ret_serv50 = 0
            valor_ret_servicios = 0
            val_ret_serv100 = 0
            impu_retencion = []
            for re in comp.l10n_ec_withhold_ids:
                total_amount = 0
                temp.update({'totalAmount': False})
                for withhold_line_id in re.l10n_ec_withhold_line_ids:
                    for tax_id in withhold_line_id.tax_ids:
                        if tax_id.tax_group_id.l10n_ec_type == 'withhold_vat_purchase':
                            if tax_id.amount == 10:
                                ret_bienes10 += withhold_line_id.l10n_ec_withhold_tax_amount
                            if tax_id.amount == 20:
                                val_ret_serv20 += withhold_line_id.l10n_ec_withhold_tax_amount
                            if tax_id.amount == 30:
                                valor_ret_bienes += withhold_line_id.l10n_ec_withhold_tax_amount
                            if tax_id.amount == 50:
                                val_ret_serv50 += withhold_line_id.l10n_ec_withhold_tax_amount
                            if tax_id.amount == 70:
                                valor_ret_servicios += withhold_line_id.l10n_ec_withhold_tax_amount
                            if tax_id.amount == 100:
                                val_ret_serv100 += withhold_line_id.l10n_ec_withhold_tax_amount
                        if tax_id.tax_group_id.l10n_ec_type == 'withhold_income_purchase':
                            existe = False
                            for tem_impu in impu_retencion:
                                if tem_impu['codRetAir'] == tax_id.description:
                                    existe = True
                                    tem_impu['baseImpAir'] = "{0:.2f}".format(
                                        float(tem_impu['baseImpAir']) + abs(withhold_line_id.balance)
                                    )
                                    tem_impu['valRetAir'] = "{0:.2f}".format(
                                        float(tem_impu['valRetAir']) + abs(withhold_line_id.l10n_ec_withhold_tax_amount)
                                    )
                                    continue
                            if not existe:
                                temp1 = {}
                                temp1.update({'codRetAir': tax_id.l10n_ec_code_ats})
                                temp1.update({'baseImpAir': str("{0:.2f}".format(abs(withhold_line_id.balance)))})
                                temp1.update({
                                    'porcentajeAir': str(
                                        int(tax_id.amount)
                                    ) if tax_id.amount == int(tax_id.amount) else f'{tax_id.amount:.2f}'
                                })
                                temp1.update({
                                    'valRetAir': str(
                                        "{0:.2f}".format(abs(withhold_line_id.l10n_ec_withhold_tax_amount))
                                    )
                                })
                                impu_retencion.append(temp1)
                            total_amount = total_amount + abs(withhold_line_id.l10n_ec_withhold_tax_amount)
                temp.update({'estabRetencion1': str(re.l10n_latam_document_number[0:3])})
                temp.update({'ptoEmiRetencion1': str(re.l10n_latam_document_number[4:7])})
                if re.name:
                    temp.update({'secRetencion1': str(re.l10n_latam_document_number[8:17])})
                else:
                    temp.update({'secRetencion1': ''})
                temp.update({'autRetencion1': str(re.l10n_ec_authorization_number)})
                temp.update({'fechaEmiRet1': self.formato_fecha(re.l10n_ec_withhold_date)})
                if total_amount != 0:
                    temp.update({'totalAmount': True})
            temp.update({'detalleAir': impu_retencion})
            temp.update({'valRetBien10': str("{0:.2f}".format(abs(ret_bienes10)))})
            temp.update({'valRetServ20': str("{0:.2f}".format(abs(val_ret_serv20)))})
            temp.update({'valorRetBienes': str("{0:.2f}".format(abs(valor_ret_bienes)))})
            temp.update({'valRetServ50': str("{0:.2f}".format(abs(val_ret_serv50)))})
            temp.update({'valorRetServicios': str("{0:.2f}".format(abs(valor_ret_servicios)))})
            temp.update({'valRetServ100': str("{0:.2f}".format(abs(val_ret_serv100)))})
            list_compras.append(temp)
        return list_compras

    def update_razon_social(self, par):
        temp_param = ''
        list_characters = par.upper()
        for car in list_characters:
            if self.CARACTERES_PERRMITIDOS.find(car) != -1:
                temp_param = temp_param + car
        return temp_param

    def generate_file(self):
        try:
            tmpl_path = os.path.join(os.path.dirname(__file__), 'template')
            env = Environment(loader=FileSystemLoader(tmpl_path))
            anexo_template = env.get_template(self.TEMPLATES['anexo_transaccional'])
            date_month_start = "%s-%s-01" % (str(self.year), str(self.month))
            date_month_end = "%s-%s-%s" % (
                str(self.year), str(self.month), calendar.monthrange(int(self.year), int(self.month))[1]
            )
            compras = self.lista_compras(date_month_start, date_month_end)
            ventas, list_ventas = self.lista_ventas(date_month_start, date_month_end)
            data = {}
            data.update({'id_informante': self.env.user.company_id.partner_id.vat})
            data.update({
                'tipo_documento': self.TIPO_IDENTIFICACION_GENERAL[
                    self.env.user.company_id.partner_id.l10n_latam_identification_type_id.name
                ]
            })
            data.update({'razon_social': self.update_razon_social(self.env.user.company_id.partner_id.name)})
            data.update({'manual': True})
            data.update({'anio': self.year})
            data.update({'mes': str(self.month).zfill(2)})
            data.update({'totalVentas': "{0:.2f}".format(ventas)})
            data.update({'codigoOperativo': 'IVA'})
            data.update({'list_compras': compras})
            data.update({'list_ventas': list_ventas})
            anexo = anexo_template.render(data)
            return self.write({
                'txt_filename': 'Anexo Transaccional.xml',
                'txt_binary': base64.standard_b64encode(anexo.encode('utf-8'))
            })
        except Exception as e:
            raise ValidationError(u'Error al generar el archivo XML: %s' % e)
        
    def name_get(self):
        result = []
        for cat in self:
            name = cat.year + '-' + cat.month
            result.append((cat.id, name))
        return result

    def lista_ventas(self, date_month_start, date_month_end):
        list_ventas = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.user.company_id.id),
            ('invoice_date', '>=', date_month_start),
            ('invoice_date', '<=', date_month_end),
            ('move_type', '=', 'out_invoice')
        ])
        ventas = {}
        ventas_total = 0
        for ven in list_ventas:
            ventas_total += ven['amount_untaxed']
            base_exempt_vat, base_zero_vat, base_vats, base_ice = self._get_vat_values(ven)
            try:
                ventas[ven.partner_id.id]['baseImponible'] = str(
                    "{0:.2f}".format(float(ventas[ven.partner_id.id]['baseImponible']) + float(base_zero_vat))
                )
                ventas[ven.partner_id.id]['baseImpGrav'] = str(
                    "{0:.2f}".format(float(ventas[ven.partner_id.id]['baseImpGrav']) + float(base_vats))
                )
                ventas[ven.partner_id.id]['montoIce'] = str(
                    "{0:.2f}".format(float(ventas[ven.partner_id.id]['montoIce']) + base_ice)
                )
                ventas[ven.partner_id.id]['montoIva'] = str("{0:.2f}".format(
                    float(ventas[ven.partner_id.id]['montoIva']) + ven.amount_tax)
                )
                valor_iva = float(ventas[ven.partner_id.id]['valorRetIva'])
                ret_rent = float(ventas[ven.partner_id.id]['valorRetRenta'])
                valor_iva, ret_rent = self._get_retention_values(ven, valor_iva, ret_rent)
                ventas[ven.partner_id.id]['numeroComprobantes'] += 1
                ventas[ven.partner_id.id]['valorRetIva'] = str("{0:.2f}".format(valor_iva))
                ventas[ven.partner_id.id]['valorRetRenta'] = str("{0:.2f}".format(ret_rent))
            except Exception:
                ventas[ven.partner_id.id] = {}
                ventas[ven.partner_id.id].update({'id': ven.id})
                ventas[ven.partner_id.id].update({
                    'tpIdCliente': str(self.TP_ID_CLIENTE[ven.partner_id.l10n_latam_identification_type_id.name])
                })
                ventas[ven.partner_id.id].update({'idCliente': str(ven.partner_id.vat)})
                ventas[ven.partner_id.id].update({'parteRelVtas': 'NO'})
                ventas[ven.partner_id.id].update({'tipoComprobante': str(ven.l10n_latam_document_type_id.code)})
                if self.env.user.company_id.type_invoice == '1':
                    ventas[ven.partner_id.id].update({'tipoEmision': 'E'})
                else:
                    ventas[ven.partner_id.id].update({'tipoEmision': 'F'})
                if ven.partner_id.l10n_latam_identification_type_id.name == 'Pasaporte':
                    ventas[ven.partner_id.id].update({'tipoCliente': '01'})
                    ventas[ven.partner_id.id].update({'nombrCliente': ven.partner_id.name})
                ventas[ven.partner_id.id].update({'numeroComprobantes': 1})
                ventas[ven.partner_id.id].update({'baseNoGraIva': f'{base_exempt_vat:.2f}'})
                ventas[ven.partner_id.id].update({
                    'baseImponible': str("{0:.2f}".format(base_zero_vat)) if int(base_exempt_vat) == 0 else "0.00"
                })
                ventas[ven.partner_id.id].update({'baseImpGrav': str("{0:.2f}".format(base_vats))})
                ventas[ven.partner_id.id].update({'montoIce': str("{0:.2f}".format(base_ice))})
                ventas[ven.partner_id.id].update({'montoIva': str("{0:.2f}".format(ven.amount_tax))})
                ventas[ven.partner_id.id].update({'formaPago': ven.l10n_ec_sri_payment_id.code})
                valor_iva = 0
                ret_rent = 0
                valor_iva, ret_rent = self._get_retention_values(ven, valor_iva, ret_rent)
                ventas[ven.partner_id.id].update({'valorRetIva': str("{0:.2f}".format(abs(valor_iva)))})
                ventas[ven.partner_id.id].update({'valorRetRenta': str("{0:.2f}".format(abs(ret_rent)))})
        total_notas, ventas_notas = self._lista_notas_credito(date_month_start, date_month_end)
        ventas_total -= total_notas
        list_resul = []
        for index, valor in ventas.items():
            list_resul.append(valor)
        for index, valor in ventas_notas.items():
            list_resul.append(valor)
        if self.env.user.company_id.type_invoice == '1':
            ventas_total = 0.00
        return ventas_total, list_resul

    @staticmethod
    def _get_vat_values(document):
        base_exempt_vat = 0.00
        base_zero_vat = 0.00
        base_vats = 0.00
        base_ice = 0.00
        for invoice_line_id in document.invoice_line_ids:
            for tax_id in invoice_line_id.tax_ids:
                if tax_id.tax_group_id.l10n_ec_type == 'exempt_vat':
                    base_exempt_vat += invoice_line_id.price_subtotal
                if tax_id.tax_group_id.l10n_ec_type == 'zero_vat':
                    base_zero_vat += invoice_line_id.price_subtotal
                if tax_id.tax_group_id.l10n_ec_type in ['vat08', 'vat12', 'vat14', 'vat15']:
                    base_vats += invoice_line_id.price_subtotal
                if tax_id.tax_group_id.l10n_ec_type == 'ice':
                    base_ice += invoice_line_id.price_subtotal
        return base_exempt_vat, base_zero_vat, base_vats, base_ice

    @staticmethod
    def _get_retention_values(document, valor_iva, ret_rent):
        for withhold_id in document.l10n_ec_withhold_ids:
            for withhold_line_id in withhold_id.l10n_ec_withhold_line_ids:
                if withhold_id.state == 'posted':
                    for tax_id in withhold_line_id.tax_ids:
                        if tax_id.tax_group_id.l10n_ec_type == 'withhold_income_sale':
                            ret_rent += abs(withhold_line_id.l10n_ec_withhold_tax_amount)
                        if tax_id.tax_group_id.l10n_ec_type == 'withhold_vat_sale':
                            valor_iva += abs(withhold_line_id.l10n_ec_withhold_tax_amount)
        return valor_iva, ret_rent
