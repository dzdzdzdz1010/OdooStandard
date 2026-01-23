# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockZeroDemandConfirmation(models.TransientModel):
    _name = 'stock.zero.demand.confirmation'
    _description = 'Zero Demand Confirmation'

    picking_ids = fields.Many2many('stock.picking')

    def process(self):
        if self.picking_ids:
            if self.env.context.get('to_validate'):
                return self.picking_ids.with_context(skip_zero_demand_check=True).button_validate()
            return self.picking_ids.with_context(skip_zero_demand_check=True).action_confirm()
        return True
