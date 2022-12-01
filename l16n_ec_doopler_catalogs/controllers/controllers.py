# -*- coding: utf-8 -*-
# from odoo import http


# class L16nEcDooplerCatalogs(http.Controller):
#     @http.route('/l16n_ec_doopler_catalogs/l16n_ec_doopler_catalogs', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l16n_ec_doopler_catalogs/l16n_ec_doopler_catalogs/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('l16n_ec_doopler_catalogs.listing', {
#             'root': '/l16n_ec_doopler_catalogs/l16n_ec_doopler_catalogs',
#             'objects': http.request.env['l16n_ec_doopler_catalogs.l16n_ec_doopler_catalogs'].search([]),
#         })

#     @http.route('/l16n_ec_doopler_catalogs/l16n_ec_doopler_catalogs/objects/<model("l16n_ec_doopler_catalogs.l16n_ec_doopler_catalogs"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l16n_ec_doopler_catalogs.object', {
#             'object': obj
#         })
