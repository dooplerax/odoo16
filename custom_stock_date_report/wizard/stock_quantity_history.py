# -*- coding: utf-8 -*-
from odoo import models, fields


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_at_date(self):
        action = super(StockQuantityHistory, self).open_at_date()

        search_view_id = self.env.ref(
            'custom_stock_date_report.view_stock_date_report_search'
        ).id
        action['search_view_id'] = [search_view_id, 'search']

        return action