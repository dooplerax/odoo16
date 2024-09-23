# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Antonio Palma Vera <antonio.palma@citytech.ec>
# Fecha: 19/09/2022
{
    'name': "Manufacturing Doopler",

    'summary': """
        Doppler output module""",

    'description': """
        Doppler output module
    """,

    'author': "Antonio Alexander Palma Vera",
    'license': 'AGPL-3',
    'website': "http://www.citytech.com",

    'category': 'Manufacturing',
    'version': '16.0',

    'depends': ['base','mrp','sale', 'sale_stock'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/production_order_views.xml',
        'views/mrp_work_center_views.xml',
        'views/mrp_production_views.xml',
    ],
    "installable": True,
}