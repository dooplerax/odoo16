odoo.define('l16n_ec_reconcile.MovBancarios', function (require) {
  'use strict'
  var AbstractAction = require('web.AbstractAction')

  var core = require('web.core')

  var QWeb = core.qweb

  //var ajax = require('web.ajax')

  var BanckMove = AbstractAction.extend({
    title: core._t('Movimientos Bancarios'),
    contentTemplate: 'l16n_ec_reconcile.mov_bancarios',
    events: {
      'click .id_btn_buscar': 'actionBuscar',
    },
    start: function () {
      var self = this
      self.listPartner()
      self.listAccount()
    },

    listPartner: function () {
      return this._rpc({
        model: 'bank.account.move',
        method: 'list_res_parther',
        args: [],
      }).then(function (result) {
        var html = QWeb.render('SelectPartner', { items: result })
        $('#id_div_clientes').html(html)
      })
    },
    listAccount: function () {
      return this._rpc({
        model: 'bank.account.move',
        method: 'list_account',
        args: [],
      }).then(function (result) {
        var html = QWeb.render('SelectAccount', { items: result })
        $('#id_select_account').html(html)
      })
    },
    actionBuscar: function () {
      var inicio = $('#id_inicio').val()

      var fecha_inicio = $('#id_fecha_desde').val()
      var fecha_hasta = $('#id_fecha_hasta').val()
      var no_documento = $('#id_nodocumento').val()
      var select = $('#id_select option:selected').val()
      var partner = $('#id_partner option:selected').val()
      var account = $('#id_cuentas option:selected').val()
      var valor = $('#id_valor').val()
      var estados = $('#id_estado option:selected').val()
      console.log('valor', valor)
      console.log('account', account)
      console.log('estado', estados)

      return this._rpc({
        model: 'bank.account.move',
        method: 'action_load_entries',
        args: [
          fecha_inicio,
          fecha_hasta,
          no_documento,
          select,
          valor,
          partner,
          account,
          estados,
          inicio,
        ],
      }).then(function (result) {
        var html = QWeb.render('TableResultLine', { items: result })
        $('#id_table_result').html(html)
      })
    },
  })
  core.action_registry.add('movimientos_bancarios', BanckMove)
  return {
    BanckMove: BanckMove,
  }
})
