# -*- coding: utf-8 -*-
{
    'name': "crons_doopler",

    'summary': """
        Acciones planificadas manuales o automaticas de Doopler""",

    'description': """
        Acciones planificadas Doopler
    """,

    'author': "Antonio Alexander Palma Vera",
    'website': "",

    'category': 'Doopler',
    'version': '0.1',

    'depends': ['base', 'contacts', 'account'],

    'data': [
        'security/ir.model.access.csv',
        'views/delete_contacts_inactive.xml',
    ],
}