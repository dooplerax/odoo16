# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Customs Ecuador EDI',
    'version': '16.0.0.6',
    'author': 'Johnny Piguave',
    'category': 'Localization',
    'complexity': 'normal',
    'license': 'AGPL-3',
    'website': '',
    'data': [
        'report/report_account_move.xml',
        'views/withholding_view.xml',
        'views/credit_note_view.xml',
    ],
    'depends': [
       'account_edi',
        'l10n_ec_edi'
    ],
    "installable": True,
}

