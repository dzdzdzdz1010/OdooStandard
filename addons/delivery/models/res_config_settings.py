# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    delivery_email_validation = fields.Boolean(
        related='company_id.delivery_email_validation',
        readonly=False,
    )
