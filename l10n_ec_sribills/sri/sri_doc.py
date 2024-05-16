
# -*- coding: utf-8 -*-
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 23/03/2021
# Requerimiento: P00038

import os
from io import StringIO
import base64
import logging

from lxml import etree
from zeep import Client
from lxml.etree import fromstring, DocumentInvalid

from odoo.exceptions import UserError

try:
    from suds.client import Client
except ImportError:
    logging.getLogger('xades.sri').info('Instalar libreria suds-jurko')

from ..models import utils


SCHEMAS = {
    'out_invoice': 'schemas/factura.xsd',
    'out_refund': 'schemas/nota_credito.xsd',
    'withdrawing': 'schemas/retencion.xsd',
    'delivery': 'schemas/guia_remision.xsd',
    'in_refund': 'schemas/nota_debito.xsd',
    'liq_purchase': 'schemas/liquidacionv1.0.0.xsd'
}


class DocumentXML(object):

    _schema = False
    document = False

    @classmethod
    def __init__(self, document, type='out_invoice'):
        """
        document: XML representation
        type: determinate schema
        """
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        self.document = fromstring(document.encode('utf-8'), parser=parser)
        self.type_document = type
        self._schema = SCHEMAS[self.type_document]
        self.signed_document = False
        self.logger = logging.getLogger('xades.sri')


    @classmethod
    def validate_xml(self):
        """
        Validar esquema XML
        """
        self.logger.info('Validacion de esquema')
        self.logger.debug(etree.tostring(self.document, pretty_print=True))
        file_path = os.path.join(os.path.dirname(__file__), self._schema)
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        try:
            xmlschema.assertValid(self.document)
            return True
        except DocumentInvalid:
            return False

    @classmethod
    def send_receipt(self, document,envairoment):

        """
        Metodo que envia el XML al WS
        """
        self.logger.info('Enviando documento para recepcion SRI')
        buf = StringIO()
        buf.write(document)
        buffer_xml = base64.encodestring(buf.getvalue())

        if not utils.check_service('prod'):
            # TODO: implementar modo offline
            raise Exception('Error SRI', 'Servicio SRI no disponible.')
        client = Client(SriService.get_active_ws(envairoment)[0])
        result = client.service.validarComprobante(buffer_xml)
        self.logger.info('Estado de respuesta documento: %s' % result.estado)
        errores = []
        if result.estado in ('RECIBIDA'):
            return True, result.estado, errores
        else:
            for comp in result.comprobantes:
                for m in comp[1][0].mensajes:
                    rs = [m[1][0].tipo, m[1][0].mensaje]
                    rs.append(getattr(m[1][0], 'informacionAdicional', ''))
                    errores.append(' '.join(rs))
            self.logger.error(errores)
            return False, result.estado, ', '.join(errores)


class SRIRequest(object):
    @classmethod
    def __init__(self):
        self.logger = logging.getLogger('xades.sri')

    def request_authorization(self, access_key):
        """
        Descarga los xml con por las autorizaicones del SRI
        Autor: Danner Marante, Davit
        Fecha: 23/03/2021
        Requerimiento: P00038
        :param access_key:
        :return:
        """
        messages = []
        client = Client('https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl')
        result = client.service.autorizacionComprobante(access_key)
        print(access_key)
        print("Respuesta de autorizacionComprobante:SRI")
        print(result)
        if result.autorizaciones:
            autorizacion = result.autorizaciones['autorizacion'][0]
            mensajes = autorizacion.mensajes
            self.logger.info('Estado de autorizacion %s' % autorizacion.estado)
            if mensajes:
                for m in mensajes:
                    self.logger.error('{0} {1}'.format(
                        m.identificador, m.mensaje)
                    )
                    messages.append([m.identificador, m.mensaje])
            if not autorizacion.estado == 'AUTORIZADO':
                return autorizacion.estado, messages
            return autorizacion.estado, autorizacion
        return False, []


class SriService(object):
    # Consumo los servicion SOAP SRI
    __AMBIENTE_PRUEBA = '1'
    __AMBIENTE_PROD = '2'
    __ACTIVE_ENV = False

    __WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    __WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'

    __WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    __WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'

    __WS_TESTING = (__WS_TEST_RECEIV, __WS_TEST_AUTH)
    __WS_PROD = (__WS_RECEIV, __WS_AUTH)

    _WSDL = {
        __AMBIENTE_PRUEBA: __WS_TESTING,
        __AMBIENTE_PROD: __WS_PROD
    }
    __WS_ACTIVE = __WS_TESTING

    @classmethod
    def set_active_env(self, env_service):
        if env_service == self.__AMBIENTE_PRUEBA:
            self.__ACTIVE_ENV = self.__AMBIENTE_PRUEBA
        else:
            self.__ACTIVE_ENV = self.__AMBIENTE_PROD

        # self.__WS_ACTIVE = self._WSDL[self.__ACTIVE_ENV]

    @classmethod
    def get_active_env(self):
        return self.__ACTIVE_ENV

    @classmethod
    def get_env_test(self):
        return self.__AMBIENTE_PRUEBA

    @classmethod
    def get_env_prod(self):
        return self.__AMBIENTE_PROD

    @classmethod
    def get_ws_test(self):
        return self.__WS_TEST_RECEIV, self.__WS_TEST_AUTH

    @classmethod
    def get_ws_prod(self):
        return self.__WS_RECEIV, self.__WS_AUTH

    @classmethod
    def get_active_ws(self, env_service):
        self.set_active_env(env_service)
        return self.__WS_ACTIVE
