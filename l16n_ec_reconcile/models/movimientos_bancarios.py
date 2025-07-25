# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import io
import xlwt

from odoo import api, models, _
from odoo.exceptions import Warning as UserError


class MovimientosBancarios(models.TransientModel):
    _name = 'bank.account.move'
    _description = 'Descripción'

    def _lines(
        self,
        fecha_inicio,
        fecha_hasta,
        no_documento,
        id_select,
        id_valor,
        partner,
        prm_account,
        estados,
        limit=False
    ):
        account = """
            select id from account_account where account_type = 'asset_cash' and company_id = %s
        """ % (str(self.env.user.company_id.id))
        self._cr.execute(account)
        list_cuentas = self._cr.fetchall()
        cuentas = ""
        where = ""
        if fecha_inicio:
            where += "and lin.date >= '{}'".format(fecha_inicio)
        if fecha_hasta:
            where += "and lin.date <= '{}'".format(fecha_hasta)
        if no_documento:
            where += "and (mov.name like '{}' or mov.payment_number like '{}')".format(no_documento, no_documento)
        if id_valor:
            valor = float(id_valor)
            if id_select == 'mayor':
                where += "and lin.balance >= {} ".format(valor)
            elif id_select == 'menor':
                where += "and lin.balance <= {}".format(valor)
            else:
                where += "and round(lin.balance::numeric, 2) = {}".format(valor)
        if int(partner) != 0:
            where += " and par.id = " + partner
        if prm_account and int(prm_account) != 0:
            where += " and lin.account_id = {}".format(prm_account)
        if estados == "conciliado":
            where += " and lin.conciled = True"
        if estados == "noconciliado":
            where += " and (lin.conciled = False or lin.conciled is Null)"
        if prm_account == 0:
            for acc in list_cuentas:
                if cuentas == "":
                    cuentas = str(acc[0])
                else:
                    cuentas += "," + str(acc[0])
            if cuentas == "":
                raise UserError(_('No hay datos para mostrar.'))
        else:
            cuentas = prm_account
        if limit:
            limite_ofset = int(limit) * 10
            sql = """
                select mov.name move_name, lin.date ,lin.name lin_name, lin.balance, mov.ref, par.name par_name,
                lin.conciled, acc.name name_account, lin.id, mov.payment_number
                from account_move_line lin
                left join res_partner par on par.id = lin. partner_id
                inner join account_move mov on mov.id = move_id
                inner join account_account acc on acc.id = lin.account_id
                where lin.account_id in (%s) %s
                order by lin.id desc limit 10 offset %s
            """ % (cuentas, where, str(limite_ofset))
        else:
            sql = """
                select mov.name move_name, lin.date, lin.name lin_name, lin.balance, mov.ref, par.name par_name,
                lin.conciled, acc.name name_account, lin.id, mov.payment_number
                from account_move_line lin
                left join res_partner par on par.id = lin. partner_id
                inner join account_move mov on mov.id = move_id
                inner join account_account acc on acc.id = lin.account_id
                where lin.account_id in (%s) %s
                order by lin.id desc
            """ % (cuentas, where)
        self._cr.execute(sql)
        return self._cr.fetchall()

    @api.model
    def list_res_parther(self):
        sql = """
        select id, name from res_partner"""
        self._cr.execute(sql)
        list_partner = self._cr.fetchall()
        json_list = [{'id': 0, 'name': 'Todos'}]
        for li in list_partner:
            json_list.append({'id': li[0], 'name': li[1]})
        return json_list

    @api.model
    def list_account(self):
        sql = """
            select id, code, name from account_account where company_id = %s and account_type = 'asset_cash'
        """ % self.env.user.company_id.id
        self._cr.execute(sql)
        list_account = self._cr.fetchall()
        json_list = [{'id': 0, 'name': 'Todos'}]
        for li in list_account:
            json_list.append({'id': li[0], 'name': li[1] + ' ' + li[2]})
        return json_list

    @staticmethod
    def validate_number(valor):
        try:
            return float(valor)
        except:
            return 0

    @api.model
    def action_load_entries(
        self,
        fecha_inicio,
        fecha_hasta,
        no_documento,
        select,
        valor,
        partner,
        account,
        estados,
        start
    ):
        list_move_lines = self._lines(
            fecha_inicio,
            fecha_hasta,
            no_documento,
            select,
            self.validate_number(valor),
            partner,
            int(account),
            estados,
            start
        )
        result = []
        for li in list_move_lines:
            conciliado = 'No'
            if li[6]:
                conciliado = 'Si'
            result.append({
                'id': li[8],
                'date': li[1],
                'name': li[0],
                'benef': li[5],
                'concepto': li[2],
                'valor': "{0:.2f}".format(li[3]),
                'conciliado': conciliado,
                'name_account': li[9],
                'account': li[7]
            })
        return result

    @api.model
    def conciliar(self, move_line_id):
        mov = self.env['account.move.line'].search([('id', '=', int(move_line_id))])
        mov.conciled = not mov.conciled
        if mov.conciled:
            mov.conciled_date = mov.date
        else:
            mov.conciled_date = None
        return mov.conciled

    @api.model
    def action_export(self, fecha_inicio, fecha_hasta, no_documento, select, valor, patner, account, estados):
        workbook = xlwt.Workbook(encoding="UTF-8")
        cabecera = xlwt.easyxf('font: name Times New Roman, color-index black, bold on', num_format_str='#,##0.00')
        worksheet = workbook.add_sheet('Reporte')
        worksheet.write_merge(0, 0, 0, 6, self.env.user.company_id.display_name, cabecera)
        worksheet.write_merge(1, 1, 0, 6, 'Reporte de Bancos', cabecera)
        worksheet.write(3, 0, 'Fecha', cabecera)
        worksheet.write(3, 1, 'Número de documento', cabecera)
        worksheet.write(3, 2, 'Número de cheque', cabecera)
        worksheet.write(3, 3, 'Cuenta', cabecera)
        worksheet.write(3, 4, 'Beneficiario', cabecera)
        worksheet.write(3, 5, 'Concepto', cabecera)
        worksheet.write(3, 6, 'Valor', cabecera)
        lineas = self._lines(fecha_inicio, fecha_hasta, no_documento, select, valor, patner, int(account), estados)
        key = 4
        for li in lineas:
            worksheet.write(key, 0, str(li[1]))
            worksheet.write(key, 1, str(li[0]))
            worksheet.write(key, 2, str(li[9]))
            worksheet.write(key, 3, str(li[7]))
            worksheet.write(key, 4, str(li[5]))
            worksheet.write(key, 5, str(li[2]))
            worksheet.write(key, 6, str("{0:.2f}".format(li[3])))
            key = key + 1
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        export_id = self.env['download.xlsx'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': 'Reporte de Bancos.xls'}
        )
        fp.close()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'download.xlsx',
            'view_type': 'form',
            'target': 'new'
        }
