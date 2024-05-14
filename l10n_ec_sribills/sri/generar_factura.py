from lxml import etree

def generarFactura(xslt_content):
    """
    Metodo para leer los xml y los combierte en json con valores para generar facturas
    :param xslt_content:
    :return:
    """
    doc = etree.fromstring(xslt_content)
    objFactura = {}
    objFactura['infoTributaria'] = {}
    objFactura['infoFactura'] = {}
    objFactura['totalConImpuestos'] = []
    objFactura['detalles'] = []
    totalImpuestos = []
    valImpuesto = {}
    valElemto= {}
    tag = ''
    tag2 = ''

    for event, element in etree.iterwalk(doc, events=('start', 'end')):
        if element.tag in ['infoTributaria', 'infoFactura', 'totalConImpuestos', 'detalles'] :
            tag = element.tag
            continue
        else:
            if tag == 'infoTributaria':
                objFactura['infoTributaria'][element.tag ] =element.text

            if tag == 'infoFactura':
                objFactura['infoFactura'][element.tag] = element.text

            if tag == 'totalConImpuestos':
                if tag2 == '' and element.tag == 'totalImpuesto':
                    tag2 = element.tag
                    continue

                elif tag2 == 'totalImpuesto' and element.tag == 'totalImpuesto':
                    totalImpuestos.append(valImpuesto)
                    valImpuesto = {}
                    tag2 = ''
                    continue

                valImpuesto[element.tag] = element.text

            if tag == 'detalles':
                if tag2 == '' and element.tag == 'detalle':
                    tag2 = element.tag
                    continue
                elif tag2 == 'detalle' and element.tag == 'detalle':
                    objFactura['detalles'].append(valElemto)
                    valElemto = {}
                    tag2 = ''
                    continue
                valElemto[element.tag] = element.text

    objFactura['totalConImpuestos'] = totalImpuestos

    return objFactura

def generarRetencion(xslt_content):
    """
        Metodo para leer los xml y los combierte en json con valores para generar Retenciones
        :param xslt_content:
        :return:
        """
    doc = etree.fromstring(xslt_content)
    objFactura = {}
    objFactura['infoTributaria'] = {}
    objFactura['infoCompRetencion'] = {}
    objFactura['impuestos'] = []
    totalImpuestos = []
    valImpuesto = {}
    tag = ''
    tag2 = ''

    for event, element in etree.iterwalk(doc, events=('start', 'end')):
        if element.tag in ['infoTributaria', 'infoCompRetencion', 'impuestos', 'detalles'] :
            tag = element.tag
            continue
        else:
            if tag == 'infoTributaria':
                objFactura['infoTributaria'][element.tag ] = element.text

            if tag == 'infoCompRetencion':
                objFactura['infoCompRetencion'][element.tag] = element.text

            if tag == 'impuestos':
                if tag2 == '' and element.tag == 'impuesto':
                    tag2 = element.tag
                    continue

                elif tag2 == 'impuesto' and element.tag == 'impuesto':
                    totalImpuestos.append(valImpuesto)
                    valImpuesto = {}
                    tag2 = ''
                    continue

                valImpuesto[element.tag] = element.text


    objFactura['impuestos'] = totalImpuestos

    return objFactura