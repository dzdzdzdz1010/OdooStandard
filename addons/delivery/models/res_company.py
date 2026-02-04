# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _default_confirmation_mail_template(self):
        try:
            return self.env.ref('delivery.mail_template_data_delivery_confirmation').id
        except ValueError:
            return False

    delivery_email_validation = fields.Boolean("Email Confirmation Delivery", default=False)
    delivery_mail_confirmation_template_id = fields.Many2one(
        'mail.template',
        string="Email Template confirmation delivery",
        domain="[('model', '=', 'delivery.note')]",
        default=_default_confirmation_mail_template,
        help="Email sent to the customer once the order is delivered.",
    )
