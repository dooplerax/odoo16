# -*- coding: utf-8 -*-
{
    'name': "Doopler catalogs",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Citytech",
    'website': "https://citytech.ec",
    'category': 'Inventary',
    'version': '0.1',
    'depends': ['base','stock','mail', 'uom', 'product', 'sale','web', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/reporte/cotizacion.xml',
        'views/product_template.xml',
        #'wizard/sale_order_pop.xml',
        'data/do_class_catalog_data.xml',
        'data/telas.xml',

    ],
    
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
