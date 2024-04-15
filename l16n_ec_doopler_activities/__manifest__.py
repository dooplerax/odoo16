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
            'views/mail.activity.view.form.popup.inherited.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
