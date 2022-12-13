odoo.define('l16n_ec_reconcile.MovBancarios', function (require) {
  'use strict'
  var AbstractAction = require('web.AbstractAction')
  var ReconciliationModel = require('account.ReconciliationModel')
  var ReconciliationRenderer = require('account.ReconciliationRenderer')
  var core = require('web.core')
  var QWeb = core.qweb

  var BanckMove = AbstractAction.extend({
    title: core._t('Movimientos Bancarios'),
    contentTemplate: 'l16n_ec_reconcile.mov_bancarios',
    CustomEvents: {},
    config: _.extend({}, AbstractAction.prototype.config, {
      // Model: ReconciliationModel.ManualModel,
      // ActionRenderer: ReconciliationRenderer.ManualRenderer,
      // LineRenderer: ReconciliationRenderer.ManualLineRenderer,
      // limitMoveLines: 15,
    }),
    start: function () {
      var self = this
      // new PartnerWidget(this).appendTo(this.$el)
      // return this._super.apply(this, arguments).then(function () {
      //   self.$el.html(
      //     QWeb.render('l16n_ec_reconcile.mov_bancarios', {
      //       widget: self,
      //     }),
      //   )
      // })
    },
  })
  // var PartnerWidget = AbstractAction.extend({
  //   contentTemplate: 'PartnerWidget',
  //   start: function () {
  //     var self = this
  //     var model = new instance.web.Model('bank.account.move')
  //     model
  //       .call('list_res_parther', {
  //         context: new instance.web.CompoundContext(),
  //       })
  //       .then(function (result) {
  //         self.$el.append(QWeb.render('SelectPartner', { item: result }))
  //       })
  //   },
  // })

  core.action_registry.add('movimientos_bancarios', BanckMove)
  return {
    BanckMove: BanckMove,
  }
})
