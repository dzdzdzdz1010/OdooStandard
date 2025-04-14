# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyHistoryLink(models.Model):
    _name = 'loyalty.history.link'
    _description = 'Mapping between issuer and redeemer loyalty history lines'

    issuer_line_id = fields.Many2one(
        string='Issuer History Line',
        comodel_name='loyalty.history',
        ondelete='cascade',
    )
    redeemer_line_id = fields.Many2one(
        string='Redeemer History Line',
        comodel_name='loyalty.history',
        ondelete='cascade',
    )
    points = fields.Float(string='Points')
