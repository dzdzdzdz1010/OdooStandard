# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Mollie Customer ID linked to this partner for payment tokenization.
    mollie_customer_id = fields.Char(copy=False)
