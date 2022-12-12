# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Conciliaciones Bancarias',
    'version': '16.0',
    'category': 'Generic Modules/Accounting',
    'license': 'AGPL-3',
    'depends': [
        'account_accountant',
    ],
    'author': 'Danner Marante',
    'website': '',
    'qweb': ['static/src/xml/*.xml'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/conciliacion.xml',
        # 'views/cargas_iniciales.xml',
        # 'views/reporte.xml',
        # 'views/extracto_reporte.xml',
        'data/sequence.xml',
        # 'wizard/conciliacion_manual.xml'
    ]
}
