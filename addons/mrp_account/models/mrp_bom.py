# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_round


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    unit_cost = fields.Float(
        'Unit Cost', company_dependent=True, digits='Product Price',
        help="Computed cost per unit of the product, based on the components and operations defined in the Bill of Materials.")
    cost_currency_id = fields.Many2one(related='product_tmpl_id.cost_currency_id')

    def action_update_product_cost_from_bom(self):
        for bom in self:
            product = bom.product_id or (bom.product_tmpl_id.product_variant_id if bom.product_tmpl_id.product_variant_count == 1 else False)
            bom.unit_cost = bom._compute_bom_cost(product, self)

    def _compute_bom_cost(self, product, boms_to_recompute):
        self.ensure_one()
        if not product:
            return 0
        total = 0

        for operation in self.operation_ids:
            if operation._skip_operation_line(product):
                continue
            total += operation.cost

        for line in self.bom_line_ids:
            if line._skip_bom_line(product):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.child_bom_id._compute_bom_cost(line.product_id, boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty

        byproduct_cost_share = sum(self.byproduct_ids.mapped('cost_share'))
        if byproduct_cost_share:
            total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)

        return self.product_uom_id._compute_price(total / self.product_qty, product.uom_id)
