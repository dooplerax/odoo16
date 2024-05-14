
# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 23/03/2021
# Requerimiento: P00038

import base64
import logging

from ..sri.sri_doc import SRIRequest
from ..sri.generar_factura import generarFactura, generarRetencion
from odoo import fields, models, api, _
from lxml import etree


class SriBillsLoad(models.Model):
    # tabla sri_bills_load
    _name = 'sri.bills.load'
    _order = "id desc"

    __logger = logging.getLogger(_name)

    descripcion = fields.Char('Descripcion')
    producto_iva0 = fields.Many2one(
        'product.template',
        'Productos Iva 0',
        required=True)
    producto_iva12 = fields.Many2one(
        'product.template',
        'Productos Iva 12',
        required=True)

    document_file = fields.Binary('Documento')
    file_name = fields.Char('Documento')
    numero_facturas = fields.Integer(string='No Documentos')
    documentos_importados = fields.Integer(string='Documentos Importados')
    documentos_error = fields.Integer(string='Documentos con Error')

    # tabla sri_bills
    documentos_id = fields.One2many('sri.bills', 'sribill_id', string='Documentos', ondelete='cascade')

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice')  # noqa
    )

    def name_get(self):
        resul = []
        for data in self:
            display_val = u'{0} '.format(
                data.descripcion or '*'
            )
            resul.append((data.id, display_val))
        return resul

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('import', 'Importado'),
            ('done', 'Generado'),
        ],
        string='Estado',
        required=True,
        default='draft'
    )

    def action_generate(self):
        """
        Lee el archivo de texto y guarda los valores
        :return:
        """
        inv_xml = SRIRequest()
        data_file = base64.b64decode(self.document_file).decode('utf-8')  # Decodifica y convierte a cadena de texto
        data_file = data_file.replace('\t\t', '\t')  # Realiza el reemplazo de texto
        lines = data_file.split('\n')
        count = 0
        total = 0
        for line in lines:
            if count > 0:
                try:
                    result = line.split('\t')
                    docu = self.documentos_id.create({
                        'ruc_emisor': result[0],
                        'razon_social_emisor': result[1],
                        'comprobante': result[2],
                        'serie_comprobante': result[3],
                        'clave_acceso': result[4],
                        'numero_autorizacion': result[4],
                        'fecha_autorizacion': result[5],
                        'fecha_emision': result[6],
                        'identificacion_receptor': result[7],
                        'importe_total': result[10],
                        'tipo_emision': 'NORMAL',
                        'sribill_id': self.id,
                        'generada': False
                    })
                    autorizacion, mesage = inv_xml.request_authorization(result[4])
                    docu.documento_firmado = mesage.comprobante
                    total += 1
                except Exception as error:
                    self.__logger.error(str(error))
            count += 1

        self.numero_facturas = total
        self.state = 'import'
        return True

    def import_documentos(self):
        """
        Importa los xml del sri por el numero de autorizacion
        :return: true
        """
        estadoGeneral = True
        for line in self.documentos_id:
            if not line.documento_firmado:
                line.generada, line.comentario = False, 'Fecha de emisión extemporánea, ocurrió un error en el SRI'
                continue
            xslt_content = str(line.documento_firmado.decode('utf-8'))
            tipo = ''
            if etree.fromstring(xslt_content).tag == 'factura':
                tipo = etree.fromstring(xslt_content).tag
                objFactura = generarFactura(xslt_content)

            if etree.fromstring(xslt_content).tag == 'comprobanteRetencion':
                tipo = etree.fromstring(xslt_content).tag
                objFactura = generarRetencion(xslt_content)

            if tipo == 'factura':
                line.generada, line.comentario = self._factura(objFactura)

            elif tipo == 'comprobanteRetencion':
                line.generada, line.comentario = self._retencion(objFactura)

            else:
                line.generada = False

            if line.generada:
                self.documentos_importados += 1
            else:
                self.documentos_error += 1
            if not line.generada and estadoGeneral:
                estadoGeneral = False

        if estadoGeneral:
            self.state = 'done'
        return True


    def _retencion(self, obj):
        """
        Metodo para generar comprobantes de retencion desde los xml del SRI
        :param obj:
        :return:
        """
        Retencion = self.env['account.retention']

        Factura = self.env['account.invoice'].search([('invoice_number', '=', obj['impuestos'][0]['numDocSustento'])])

        Cliente = self.env['res.partner'].search([('l10n_latam_identification_type_id', '=', obj['infoTributaria']['ruc'])])

        if Cliente.id and Factura.id:
            arrFechaEmision = obj['infoCompRetencion']['fechaEmision'].split('/')
            fechaEmision = "{}-{}-{}".format(arrFechaEmision[2], arrFechaEmision[1], arrFechaEmision[0])

            ret = Retencion.create({
                # 'type': 'in_invoice',
                'partner_id': Cliente.id,
                'name': "{}{}{}".format(obj['infoTributaria']['ptoEmi'], obj['infoTributaria']['estab'],
                                        obj['infoTributaria']['secuencial']),
                'claveacceso': obj['infoTributaria']['claveAcceso'],
                'date': fechaEmision,
                'type_invoice': 'electronica',
                'in_type': 'ret_out_invoice',
                'invoice_id': Factura.id,
                'manual': True,
                'numero_contribucion': False,
                'currency_id': 3,
                'to_cancel': False,
                'tax_ids': []
            })
            for imp in obj['impuestos']:
                if imp['codigoRetencion'] == '2':
                    tax = self.env['account.tax'].search(
                        [('description', '=', "609-{}".format(imp['porcentajeRetener'])), ('active', '=', True)],
                        limit=1)
                else:
                    tax = self.env['account.tax'].search(
                        [('description', '=', imp['codigoRetencion']), ('active', '=', True)], limit=1)
                if tax.id:
                    ret.tax_ids.create({
                        'name': tax.description,
                        'sequence': 0,
                        'tax_id': tax.id,
                        'manual': True,
                        'retention_id': ret.id,
                        'amount': -1 * float(imp['valorRetenido']),
                        'account_analytic_id': False,
                        'group_id': tax.tax_group_id.id,
                        'account_id': tax.account_id.id,
                        'base': imp['baseImponible']
                    })

            return True, 'Generado'
        else:
            return False, 'Cliente o Factura no registrada'


    def _factura(self, obj):
        """
        Metodo para generar las facturas desde los xml del SRI
        :param obj:
        :return:
        """
        try:
            Factura = self.env['account.invoice']
            Cliente = self.env['res.partner'].search([('indentifier', '=', obj['infoTributaria']['ruc'])])

            if Cliente.id:
                arrFechaEmision = obj['infoFactura']['fechaEmision'].split('/')
                fechaEmision = "{}-{}-{}".format(arrFechaEmision[2], arrFechaEmision[1], arrFechaEmision[0])
                auth = None
                for aut in Cliente.authorisation_ids:
                    if aut.serie_emision == obj['infoTributaria']['ptoEmi'] and aut.serie_entidad == \
                            obj['infoTributaria']['estab']:
                        auth = aut.id
                if auth == None:
                    auth = self.env['account.authorisation'].create({
                        'is_electronic': True,
                        'serie_emision': obj['infoTributaria']['ptoEmi'],
                        'serie_entidad': obj['infoTributaria']['estab'],
                        'type_id': 1,
                        'num_end': 0,
                        'partner_id': Cliente.id
                    })

                no_fact = "{}{}{}".format(obj['infoTributaria']['estab'], obj['infoTributaria']['ptoEmi'],
                                          obj['infoTributaria']['secuencial'])
                existe = Factura.search([('invoice_number', '=', no_fact), ('partner_id', '=', Cliente.id)])

                if existe.id:
                    return True, 'Documento Registrado'

                diario = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)

                fact = Factura.create({
                    'journal_id': diario.id,
                    'type': 'in_invoice',
                    'partner_id': Cliente.id,
                    'reference': obj['infoTributaria']['secuencial'],
                    'auth_number': obj['infoTributaria']['claveAcceso'],
                    'date_invoice': fechaEmision,
                    'auth_inv_id': auth,
                    'epayment_id': 1,
                    'sustento_id': 2
                })

                account_id = self.env['account.account'].search(
                    [('company_id', '=', self.env.user.company_id.id)],
                    limit=1)

                for prod in obj['detalles']:
                    if float(prod['valor']) != 0:
                        product = self.env['product.product'].search([('product_tmpl_id', '=', self.producto_iva12.id)],
                                                                     limit=1)
                    else:
                        product = self.env['product.product'].search([('product_tmpl_id', '=', self.producto_iva0.id)],
                                                                     limit=1)
                    val = {
                        'product_id': product.id,
                        'detalle': '{}'.format(prod['descripcion']),
                        'name': str(self.producto_iva12.name),
                        'quantity': prod['cantidad'],
                        'price_unit': prod['precioUnitario'],
                        'price_subtotal': prod['precioTotalSinImpuesto'],
                        'account_id': account_id.id,
                        'invoice_id': fact.id
                    }
                    line_id = self.env['account.invoice.line'].create(val)
                    line_id._onchange_product_id()
                fact._onchange_journal_id()
                fact._onchange_invoice_line_ids()

                return True, 'Generado'
            else:
                return False, 'Cliente no Registrado'

        except Exception as e:
            self.__logger.error(e.message)
            return False, e.message

