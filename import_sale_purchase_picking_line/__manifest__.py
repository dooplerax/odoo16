# -*- coding: utf-8 -*-
{
    "name": "Import doopler details",
    'summary': 'Import doopler details',
    'description': """Import Purchase/Sale/Picking Line""",
    "version":"1.0",
    "category": "Custom/Custom",
    'author': 'Antonio Alexander Palma Vera',
    'website': "https://citytech.ec",
    "depends": ['stock', 'sale', 'purchase'],
    "data": [
        'security/ir.model.access.csv',
        
        #'views/purchase_order_view.xml',
        'views/sale_order_view.xml',
        #'views/stock_picking_view.xml',

        'wizard/line_import_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
