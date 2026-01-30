# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers import main


class WebsiteSale(main.WebsiteSale):
    def _check_delivery_address(self, partner_sudo):
        """Check that currently saved shipping address is compliant with Gelato requirements.

        :param res.partner partner_sudo: The partner whose delivery address to check.
        :return: Whether all checked fields are within length limit.
        :rtype: bool
        """
        res = super()._check_delivery_address(partner_sudo)
        order_sudo = request.cart
        if not res or not order_sudo:
            return res

        return not (
            any(order_sudo.order_line.product_id.mapped('gelato_product_uid'))
            and partner_sudo._gelato_check_partner_address_exceeds_length_limit()
        )
