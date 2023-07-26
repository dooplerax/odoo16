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
<<<<<<< HEAD
    'images' : [],
    'depends' : ['base','mail','crm','sale'],
    'data': [
            'security/ir.model.access.csv',
            'views/mail.activity.view.form.popup.inherited.xml'
        ],
=======
    'images': [],
    'depends': ['base', 'mail', 'crm', 'sale', 'account'],
    'data': [
            'views/mail.activity.view.form.popup.inherited.xml'
    ],
>>>>>>> F2777
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
