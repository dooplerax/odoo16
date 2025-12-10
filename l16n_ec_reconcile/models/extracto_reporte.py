# -*- coding: utf-8 -*-
# © <2019> <Danner Marante Jacas>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class extracto_reporte(models.AbstractModel):
    _name = 'report.l16n_ec_reconcile.extracto_reporte'
    _description = 'Descripción'
    _auto = False

    def _list_no_concilied(self, account, date):
        total = 0.0
        lista_mes = []
        list_mese_anterioreres = []
        sql = """
            SELECT par.name,mov.name move_name,lin.date, lin.balance
            FROM account_move_line lin
            left join res_partner par on par.id = lin.partner_id
            inner join account_move mov
            on mov.id = lin.move_id
            WHERE lin.account_id = %s
            AND lin.date <= '%s' and (conciled = false or conciled is null or conciled_date > '%s')
            order by lin.date
        """ % (account, date, date)
        self.env.cr.execute(sql)
        account_move_lines = self.env.cr.dictfetchall()
        for li in account_move_lines:
            total += li['balance'] * -1
            li['balance'] = li['balance'] * -1
            lista_mes.append(li) if li['date'] == date else list_mese_anterioreres.append(li)
        return total, lista_mes, list_mese_anterioreres

    @api.model
    def _get_report_values(self, docids, data):
        # self.model = self.env.context.get('active_model')
        extraxto = self.env['account.bank.reconcile'].browse(docids)

        total_mov, list_mov_noconciliados, list_mov_noconciliados_mese = self._list_no_concilied(
            extraxto.journal_id.default_account_id.id,
            extraxto.date_stop)

        return {
            'doc_ids': self.ids,
            # 'doc_model': self.model,
            'docs': extraxto,
            # 'cheques_no_cobrados': list_cheques,
            # 'total_cheques': total,
            'list_mov_noconciliados': list_mov_noconciliados,
            'list_mov_noconciliados_mes': list_mov_noconciliados_mese,
            'total_mov': total_mov,
        }
