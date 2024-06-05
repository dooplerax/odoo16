# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Doopler Activities",
    'version': '1.0',
    'author': "Sebastian Falconi",
    'category': 'Category',
    'description': """
    """,
    'category': 'CRM/Activities',
    'website': "https://citytech.ec",
    'images': [],
    'depends': ['base', 'mail', 'crm', 'sale', 'account', 'stock'],
    'data': [
            'security/ir.model.access.csv',
            'views/mail.activity.view.form.popup.inherited.xml',
            'views/stock_move_line.xml',
            'views/payments_methods.xml',
            'views/account_journal_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
