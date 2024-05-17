# -*- coding: utf-8 -*-
# © <2021> <Danner Marante>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Ecuador - Facturas SRI',
    'version': '10.0.0.0.0',
    'category': 'Localisation/account',
    'author': 'Danner Marante',
    'website': '',
    'license': 'AGPL-3',
    'depends': [
        'account', 'contacts'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/srifact.xml',
        # 'views/authorisation_view.xml'
    ]
}
