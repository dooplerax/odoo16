# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Danner Marante Jacas <danner.marante@citytech.ec>
# Fecha: 18/10/2022
# Requerimiento:

{
    'name': 'Establecimientos y autorizaciones del SRI',
    'version': '16.0.0.1.1',
    'author': 'Danner Marante',
    'category': 'Localization',
    'complexity': 'normal',
    'license': 'AGPL-3',
    'website': '',
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_view.xml',
        'views/billing_location.xml',
        # 'data/account.ats.sustento.csv',
    ],
    'depends': [
       'l16n_ec_partner', 'base'
    ],
    "installable": True,
}
