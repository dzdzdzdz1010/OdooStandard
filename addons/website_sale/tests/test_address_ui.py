# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestCheckoutAddressUi(HttpCase, WebsiteSaleCommon):
    """Test the address selection UI on the checkout page."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.address_user = new_test_user(cls.env, login='address_user', groups='base.group_portal')
        cls.main_delivery_address = cls.env['res.partner'].create({
            'parent_id': cls.address_user.partner_id.id,
            'type': 'delivery',
            'name': 'Main Address',
            'street': 'Street',
            'city': 'City',
            'state_id': cls.env.ref('base.state_us_1').id,
            'zip': '12345',
            'country_id': cls.env.ref('base.us').id,
            'email': 'test@example.com',
            'phone': '+1234567890',
        })
        cls.main_billing_address = cls.main_delivery_address.copy({'type': 'invoice'})
        cls.second_delivery_address = cls.main_delivery_address.copy({'name': 'Second Address'})
        cls.main_delivery_address.copy({
            'name': 'Main Sub-level Address',
            'parent_id': cls.main_delivery_address.id,
        })
        cls.main_delivery_address.copy({
            'name': 'Second Sub-level Address',
            'parent_id': cls.second_delivery_address.id,
        })

    def test_display_first_level_delivery_addresses_only(self):
        """
        Ensure users can only select main or first-level delivery addresses from the checkout page.
        They may still create sub-addresses (via the pick-up store location) selection but these
        shouldn't be displayed.
        """
        so = self._create_so(partner_id=self.address_user.partner_id.id)
        checkout_page_values = WebsiteSale()._prepare_checkout_page_values(so)
        self.assertEqual(len(checkout_page_values['delivery_addresses']), 3)
