# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        """Override of `sale` to archive guest contacts."""
        confirmed_orders = super()._check_amount_and_confirm_order()
        confirmed_orders.filtered('website_id')._archive_partner_if_no_user()
        return confirmed_orders

    def _process(self, provider_code, payment_data):
        """Override of `payment` to allow retrying if transaction is canceled or has an error, by
        redirecting to payment page."""
        tx = super()._process(provider_code, payment_data)
        if tx.sale_order_ids.website_id and tx.state in ["cancel", "error"]:
            tx["landing_route"] = "/shop/payment"
        return tx
