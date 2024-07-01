from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_datetime, formatLang
import logging

_logger = logging.getLogger(__name__)

class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    courtain_type = fields.Selection(
        selection='_get_tipo_cortina_options', string="Tipo Cortina")

    subclass_inherit = fields.Many2one(
        'subproduct.dosubclass', 'Subclase de producto')

    fa_class_inherit = fields.Many2one(
        'fproduct.dofamily', 'Familia de producto')

    @api.model
    def _get_tipo_cortina_options(self):
        return [
            ('enrollable', 'Enrollable'),
            ('zebra', 'Zebra'),
            ('romana', 'Romana'),
            ('panelada', 'Panelada'),
            ('claraboya', 'Claraboya'),
            ('triple_shade', 'Triple Shade'),
            ('divergence', 'Divergence'),
            ('tradicional', 'Tradicional'),
            ('horizontal', 'Horizontal'),
            ('vertical', 'Vertical'),
            ('tradicional_onda_perfecta', 'Tradicional onda perfecta'),
            ('tradicional_con_pliegues', 'Tradicional con pliegues'),
        ]

# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    def _get_product_rule(self, product, quantity, courtain_type, material, uom=None, date=False, **kwargs):
        """Compute the pricelist price & rule for the specified product, qty & uom.

        Note: self.ensure_one()

        :returns: applied pricelist rule id
        :rtype: int or False
        """
        self.ensure_one()
        return self._compute_price_rule(
            product, quantity, courtain_type, material, uom=uom, date=date, **kwargs
        )[product.id][1]

    def _compute_price_rule(self, products, qty, courtain_type, material, uom=None, date=False, **kwargs):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        :param products: recordset of products (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions
        :type date: date or datetime

        :returns: product_id: (price, pricelist_rule)
        :rtype: dict
        """
        self.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        # Fetch all rules potentially matching specified products/templates/categories and date
        rules = self._get_applicable_rules(products, date, courtain_type, material, **kwargs)

        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']

            product_uom = product.uom_id
            target_uom = uom or product_uom  # If no uom is specified, fall back on the product uom

            # Compute quantity in product uom because pricelist rules are specified
            # w.r.t product default UoM (min_quantity, price_surchage, ...)
            if target_uom != product_uom:
                qty_in_product_uom = target_uom._compute_quantity(qty, product_uom, raise_if_failure=False)
            else:
                qty_in_product_uom = qty

            for rule in rules:
                if rule._is_applicable_for(product, qty_in_product_uom):
                    suitable_rule = rule
                    break

            kwargs['pricelist'] = self
            price = suitable_rule._compute_price(product, qty, target_uom, date=date, currency=self.currency_id)
            results[product.id] = (price, suitable_rule.id)
            print(f"Computed Price for Product {product.id}: {price}")

        return results

    def _get_applicable_rules(self, products, date, courtain_type, material, **kwargs):
        self.ensure_one()
        # Do not filter out archived pricelist items, since it means current pricelist is also archived
        # We do not want the computation of prices for archived pricelist to always fallback on the Sales price
        # because no rule was found (thanks to the automatic orm filtering on active field)
        return self.env['product.pricelist.item'].with_context(active_test=False).search(
            self._get_applicable_rules_domain(courtain_type, material, products=products, date=date, **kwargs)
        )

    def _get_applicable_rules_domain(self, courtain_type, material, products, date, **kwargs):
        if products._name == 'product.template':
            templates_domain = ('product_tmpl_id', 'in', products.ids)
            products_domain = ('product_id.product_tmpl_id', 'in', products.ids)

        else:
            templates_domain = ('product_tmpl_id', 'in', products.product_tmpl_id.ids)
            products_domain = ('product_id', 'in', products.ids)

        # Convertir courtain_type a lista si no lo es
        if not isinstance(courtain_type, (list, tuple)):
            courtain_type = [courtain_type]

        # Asegurarse de que subclass_inherit y fa_class_inherit sean listas
        subclass_inherit_ids = material.subclass_inherit.ids if material.subclass_inherit else []
        fa_class_inherit_ids = material.fa_class_inherit.ids if material.fa_class_inherit else []

        domain = [
            ('pricelist_id', '=', self.id),
            '|', ('categ_id', '=', False), ('categ_id', 'parent_of', products.categ_id.ids),
            '|', ('product_tmpl_id', '=', False), templates_domain,
            '|', ('product_id', '=', False), products_domain,
            '|', ('date_start', '=', False), ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
            '|', ('courtain_type', '=', False), ('courtain_type', 'in', courtain_type),
            '|', ('subclass_inherit', '=', False), ('subclass_inherit', 'in', subclass_inherit_ids),
            '|', ('fa_class_inherit', '=', False), ('fa_class_inherit', 'in', fa_class_inherit_ids),
        ]

        print("Generated domain:", domain)  # Imprimir el dominio generado
        #print("Generated domain:", domain)  # Imprimir el dominio generado
        _logger.info("TEST DE LISTADO")

        # Ejecutar la búsqueda manualmente
        pricelist_items = self.env['product.pricelist.item'].search(domain)
        print("Pricelist items found:", pricelist_items)

        return domain

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('courtain_type', 'material')
    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'courtain_type', 'material')
    def _compute_pricelist_item_id(self):
        for line in self:
            if not line.product_id or line.display_type or not line.order_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                pricelist_id = line.order_id.pricelist_id
                product = line.product_id
                quantity = line.product_uom_qty or 1.0
                uom = line.product_uom
                date = line.order_id.date_order

                # Obtener la regla de precios aplicable
                rule_id = pricelist_id._get_product_rule(product, quantity, line.courtain_type, line.material, uom=uom,
                                                         date=date)

                # Si se encontró una regla de precios, actualizar el precio en la línea de pedido
                if rule_id:
                    # Obtener el precio utilizando la regla de precios
                    price = pricelist_id.with_context(date=date)._compute_price_rule(
                        product, quantity, line.courtain_type, line.material, uom=uom, date=date
                    )[product.id][0]

                    # Actualizar la línea de pedido con el precio calculado
                    line.write({
                        'pricelist_item_id': rule_id,
                        'price_unit': price,
                    })
                else:
                    line.pricelist_item_id = False
                    line.price_unit = product.list_price  # Otra acción en caso de no encontrar regla de precios







