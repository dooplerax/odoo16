# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Payments Ecuador',
    'version': '16.0.0.0.6',
    'category': 'Generic Modules/Accounting',
    'license': 'AGPL-3',
    'depends': [
        'account', 'l10n_ec', 'account_edi'
    ],
    'author': 'Danner Marante',
    'website': '',
    'data': [
        # 'security/ir.model.access.csv',
        'wizard/account_payment_register.xml',
        'views/account_payment.xml',
        'views/account_move_views.xml'
    ]
}
