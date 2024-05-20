
# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 23/03/2021
# Requerimiento: P00038

import base64
import logging
import time
import chardet

from ..sri.sri_doc import SRIRequest
from ..sri.generar_factura import generarFactura, generarRetencion
from odoo import fields, models, api, _
import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime
from odoo.exceptions import (
    ValidationError,
    Warning as UserError
)


class SriBillsLoad(models.Model):
    # tabla sri_bills_load
    _name = 'sri.bills.load'
    _order = "id desc"

    __logger = logging.getLogger(_name)

    descripcion = fields.Char('Descripción')
    producto_iva0 = fields.Many2one(
        'product.template',
        'Productos sin IVA',
        required=True)
    producto_iva12 = fields.Many2one(
        'product.template',
        'Productos con IVA',
        required=True)

    document_file = fields.Binary('Documento')
    file_name = fields.Char('Documento')
    numero_facturas = fields.Integer(string='No Documentos')
    documentos_importados = fields.Integer(string='Documentos Importados')
    documentos_error = fields.Integer(string='Documentos con Error')
    existing_invoice_id = fields.Many2one('account.move', string="Factura Existente")
    create_partner = fields.Boolean("¿Crear provedoores no existentes?", default=True)

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

        # Detectar la codificación del archivo
        raw_data = base64.b64decode(self.document_file)
        result = chardet.detect(raw_data)
        encoding = result['encoding']

        if not encoding:
            raise ValidationError("No se pudo detectar la codificación del archivo.")

        # Decodificar utilizando la codificación detectada
        try:
            data_file = raw_data.decode(encoding)
        except UnicodeDecodeError as e:
            raise ValidationError(f"Error al decodificar el archivo: {e}")

        required_fields = [
            'RUC_EMISOR', 'RAZON_SOCIAL_EMISOR', 'TIPO_COMPROBANTE', 'SERIE_COMPROBANTE',
            'CLAVE_ACCESO', 'FECHA_AUTORIZACION', 'FECHA_EMISION', 'IDENTIFICACION_RECEPTOR',
            'VALOR_SIN_IMPUESTOS', 'IVA', 'IMPORTE_TOTAL'
        ]

        #Obtener la primera fila
        lines = data_file.split('\n')
        header = lines[0].split('\t')

        #Comprobar campos faltantes
        missing_fields = [field for field in required_fields if field not in header]
        if missing_fields:
            raise ValidationError(f"Faltan los siguientes campos en el archivo: {', '.join(missing_fields)}")

        #Realiza el reemplazo de texto
        data_file = data_file.replace('\t\t', '\t')
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

            xslt_content = line.documento_firmado.encode('utf-8')  # Convertir la cadena a bytes con codificación UTF-8
            comprobante_num = line.serie_comprobante
            tipo = ''

            try:
                root = etree.fromstring(xslt_content)
                tipo = root.tag

                if tipo == 'factura':
                    objFactura = generarFactura(xslt_content)
                elif tipo == 'comprobanteRetencion':
                    objFactura = generarRetencion(xslt_content)
                else:
                    raise ValueError(f'Tipo desconocido: {tipo}')

                if tipo == 'factura':
                    line.generada, line.comentario = self._factura(objFactura,xslt_content,comprobante_num)
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

                existe_fact = self.env['account.move'].search(
                    [('l10n_latam_document_number_stored', '=', line.serie_comprobante)], limit=1)

                if existe_fact:
                    line.existing_invoice_id = existe_fact.id
                else:
                    line.existing_invoice_id = False

            except etree.XMLSyntaxError as e:
                # Capturar y registrar el error de manera más detallada
                self.logger.error(f"Error al analizar el XML en documento_id {line.id}: {e}")
                self.logger.error(f"Contenido del XML: {xslt_content}")
                # Establecer estadoGeneral en False si se produce un error
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


    def _factura(self, obj, xslt_content, comprobante_num):
        """
        Metodo para generar las facturas desde los xml del SRI
        :param obj:
        :return:
        """
        try:
            root = ET.fromstring(xslt_content)
            Cliente = self.env['res.partner'].search([('vat', '=', obj['infoTributaria']['ruc'])], limit=1)
            cuenta_pagar = self.env['account.account'].search([('name', '=', 'Proveedores'), ('account_type', '=', 'liability_payable')], limit=1)
            country_default = self.env['res.country'].search([('name', '=', 'Ecuador')], limit=1)
            state_id = self.env['res.country.state'].search([('name', '=', 'Pichincha')], limit=1)
            email_default = 'none@gmail.com'
            street1_default = 'none'
            street2_default = 'none'
            country_default_id = country_default.id
            city_default = 'none'
            state_id_default = state_id.id

            # for campo in root.findall(".//campoAdicional"):
            #     if campo.get('nombre') == 'Email1':
            #         email = campo
            #         break
            #
            # dir_establecimiento = root.find(".//dirEstablecimiento")

            if self.create_partner == True:
                if not Cliente:
                    Cliente = self.env['res.partner'].create({
                        'name': obj['infoTributaria']['razonSocial'],
                        'vat': obj['infoTributaria']['ruc'],
                        'street': street1_default,
                        'street2': street2_default,
                        'city': city_default,
                        'state_id': state_id_default,
                        'country_id': country_default_id,
                        'email': email_default,
                        'property_account_payable_id': cuenta_pagar.id,
                        'company_type': 'company',
                        # 'customer_rank': 1,
                    })
                    print("Cliente creado", Cliente.name)
                else:
                    print("Cliente encontrado", Cliente.name)

            Cliente_search = self.env['res.partner'].search([('vat', '=', obj['infoTributaria']['ruc'])], limit=1)

            if Cliente_search:
                print("Cliente encontrado", Cliente_search.name)
                arrFechaEmision = obj['infoFactura']['fechaEmision'].split('/')
                fechaEmision = "{}-{}-{}".format(arrFechaEmision[2], arrFechaEmision[1], arrFechaEmision[0])
                auth = None
                for aut in Cliente_search.authorisation_ids:
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
                        'partner_id': Cliente_search.id
                    })

                no_fact = "{}{}{}".format(obj['infoTributaria']['estab'], obj['infoTributaria']['ptoEmi'],
                                          obj['infoTributaria']['secuencial'])

                existe = self.env['account.move'].search([('l10n_latam_document_number_stored', '=', comprobante_num)])

                if existe.id:
                    return True, 'Documento Existente'

                diario = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)

                print("journal_id:", diario.name)
                print("partner_id:", Cliente_search.name)
                print("l10n_ec_authorization_number:", obj['infoTributaria']['claveAcceso'])
                print("Secuencial:", obj['infoTributaria']['secuencial'])

                fact = self.env['account.move'].create({
                    'move_type': 'in_invoice',
                    'partner_id': Cliente_search.id,
                    'journal_id': diario.id,
                    'ref': obj['infoTributaria']['secuencial'],
                    'l10n_ec_authorization_number': obj['infoTributaria']['claveAcceso'],
                    'invoice_date': fechaEmision,
                    'l10n_latam_document_number': comprobante_num,
                    # 'auth_inv_id': auth,
                    # 'epayment_id': 1,
                    # 'sustento_id': 2
                })

                account_id = self.env['account.account'].search(
                    [('company_id', '=', self.env.user.company_id.id)],
                    limit=1)

                for prod in obj['detalles']:
                    if float(prod['valor']) != 0:
                        product = self.env['product.product'].search([('id', '=', self.producto_iva12.id)],
                                                                     limit=1)
                    else:
                        product = self.env['product.product'].search([('id', '=', self.producto_iva0.id)],
                                                                     limit=1)
                    val = {
                        'product_id': product.id,
                        # 'model': '{}'.format(prod['descripcion']),
                        'name': str(self.producto_iva12.name),
                        'quantity': prod['cantidad'],
                        'price_unit': prod['precioUnitario'],
                        'price_subtotal': prod['precioTotalSinImpuesto'],
                        'account_id': account_id.id,
                        'move_id': fact.id
                    }
                    line_id = self.env['account.move.line'].create(val)
                #     line_id._onchange_product_id()
                # fact._onchange_journal_id()
                # fact._onchange_invoice_line_ids()

                return True, 'Generado'
            else:
                return False, 'Cliente no Registrado'

        except Exception as e:
            self.__logger.error(str(e))
            return False, str(e)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    authorisation_ids = fields.One2many(
        'account.authorisation',
        'partner_id',
        'Autorizaciones'
    )

class AccountAuthorisation(models.Model):
    _name = 'account.authorisation'
    _order = 'expiration_date desc'

    @api.depends('type_id', 'num_start', 'num_end')
    def name_get(self):
        """
        Nombre
        :return:
        """
        res = []
        for record in self:
            name = u'%s. estab: (%s-%s) serie: (%s-%s) ' % (
                record.type_id.code,
                record.serie_entidad,
                record.serie_emision,
                record.num_start,
                record.num_end
            )
            res.append((record.id, name))
        return res

    @api.depends('expiration_date')
    def _compute_active(self):
        """
        Calcula si esta activo el documento con las fechas
        :return:
        """
        if self.is_electronic:
            self.active = True
        if not self.expiration_date:
            return
        now = datetime.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d')
        due_date = datetime.strptime(self.expiration_date, '%Y-%m-%d')
        self.active = now < due_date

    def _get_type(self):
        return self._context.get('type', 'in_invoice')  # pylint: disable=E1101

    def _get_in_type(self):
        return self._context.get('in_type', 'externo')

    def _get_partner(self):
        """
        Calcula el partnet
        :return:
        """
        partner = self.env.user.company_id.partner_id
        if self._context.get('partner_id'):
            partner = self._context.get('partner_id')
        return partner

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, values):
        """
        modica el create
        :param values:
        :return:
        """
        res = self.search([('partner_id', '=', values['partner_id']),
                           ('type_id', '=', values['type_id']),
                           ('serie_entidad', '=', values['serie_entidad']),
                           ('serie_emision', '=', values['serie_emision']),
                           ('serie_emision', '=', values['serie_emision']),
                           ('active', '=', True)])

        partner_id = self.env.user.company_id.partner_id.id
        if values['partner_id'] == partner_id:
            typ = self.env['account.ats.doc'].browse(values['type_id'])
            name_type = '{0}_{1}'.format(values['name'], values['type_id'])
            if values['num_start'] == 0 or not values['num_start']:
                values['num_start'] =1
            sequence_data = {
                'code': typ.code == '07' and 'account.retention' or 'account.invoice',  # noqa
                'name': name_type,
                'padding': 9,
                'number_next': values['num_start'],
            }
            seq = self.env['ir.sequence'].create(sequence_data)
            values.update({'sequence_id': seq.id})
        return super(AccountAuthorisation, self).create(values)

    def unlink(self):
        """
        Modifica el eliminar
        :return:
        """
        inv = self.env['account.invoice']
        res = inv.search([('auth_inv_id', '=', self.id)])
        if res:
            raise UserError(
                'Esta autorización esta relacionada a un documento.'
            )
        return super(AccountAuthorisation, self).unlink()

    name = fields.Char('Num. de Autorización', size=128)
    serie_entidad = fields.Char('Serie Entidad', size=3, required=True)
    serie_emision = fields.Char('Serie Emision', size=3, required=True)
    num_start = fields.Integer('Desde')
    num_end = fields.Integer('Hasta')
    is_electronic = fields.Boolean('Documento Electrónico ?')
    expiration_date = fields.Date('Fecha de Vencimiento')
    address = fields.Text('Direccion de Establecimiento')
    active = fields.Boolean(
        compute='_compute_active',
        string='Activo',
        store=True,
        default=True
    )
    in_type = fields.Selection(
        [('interno', 'Internas'),
         ('externo', 'Externas')],
        string='Tipo Interno',
        readonly=True,
        change_default=True,
        default=_get_in_type
    )
    type_id = fields.Many2one(
        'account.ats.doc',
        'Tipo de Comprobante',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        'Empresa',
        required=True,
        default=_get_partner
    )

    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        change_default=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id.id  # noqa
    )

    sequence_id = fields.Many2one(
        'ir.sequence',
        'Secuencia',
        help='Secuencia Alfanumerica para el documento, se debe registrar cuando pertenece a la compañia',  # noqa
        ondelete='cascade'
    )

    _sql_constraints = [
        ('number_unique',
         'unique(partner_id,expiration_date,type_id)',
         u'La relación de autorización, serie entidad, serie emisor y tipo, debe ser única.'),  # noqa
    ]

    def is_valid_number(self, number):
        """
        Metodo que verifica si @number esta en el rango
        de [@num_start,@num_end]
        """
        if self.is_electronic:
            return True
        if self.num_start <= number <= self.num_end:
            return True
        return False
