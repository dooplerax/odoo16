# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Stados de cuentas',
    'version': '16.0',
    'category': 'Generic Modules/Accounting',
    'license': 'AGPL-3',
    'depends': [
        'account',
    ],
    'author': 'Danner Marante',
    'website': '',
    'data': [
        'security/ir.model.access.csv',
        # 'views/client_statements.xml',
        'wizard/custom_paper_format.xml',
        'wizard/account_statements.xml',
        'wizard/partner_invoice_report.xml',
        'views/partner_report_template.xml'
    ]
}
