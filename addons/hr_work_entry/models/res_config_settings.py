# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tracking_method = fields.Selection(string='Default Tracking', related='company_id.tracking_method', readonly=False)
