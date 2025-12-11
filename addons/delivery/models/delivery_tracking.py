# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class DeliveryTracking(models.Model):
    _name = "delivery.tracking"
    _description = "Delivery"

    allowed_carrier_ids = fields.Many2many(
        comodel_name='delivery.carrier',
        compute='_compute_allowed_carrier_ids'
    )
    carrier_id = fields.Many2one(
        string="Carrier",
        comodel_name="delivery.carrier",
        domain="[('id', 'in', allowed_carrier_ids)]",
        check_company=True,
    )
    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
    carrier_tracking_url = fields.Char(
        string='Tracking URL',
        compute='_compute_carrier_tracking_url'
    )

    def _compute_allowed_carrier_ids(self):
        for tracking in self:
            carriers = self.env['delivery.carrier'].search([])
            tracking.allowed_carrier_ids = carriers

    @api.depends('carrier_id', 'carrier_tracking_ref')
    def _compute_carrier_tracking_url(self):
        for tracking in self:
            tracking.carrier_tracking_url = (
                tracking.carrier_id.get_tracking_link(tracking)
                if tracking.carrier_id and tracking.carrier_tracking_ref
                else False
            )
