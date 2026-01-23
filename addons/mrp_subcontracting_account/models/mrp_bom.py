# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _compute_bom_cost(self, product, boms_to_recompute):
        """ Add the price of the subcontracting supplier if it exists with the bom configuration.
        """
        price = super()._compute_bom_cost(product, boms_to_recompute)
        if self.type == 'subcontract':
            seller = product._select_seller(quantity=self.product_qty, uom_id=self.product_uom_id, params={'subcontractor_ids': self.subcontractor_ids})
            if seller:
                seller_price = seller.currency_id._convert(seller.price, self.env.company.currency_id, (self.company_id or self.env.company), fields.Date.today())
                price += seller.product_uom_id._compute_price(seller_price, product.uom_id)
        return price
