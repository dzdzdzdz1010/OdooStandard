# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(StripeCommon, PaymentHttpCommon):
    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a redirect notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with (
            patch('odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a webhook notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with (
            patch('odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
            ) as process_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_redirect_notification_triggers_signature_check(self):
        """Test that receiving a redirect notification triggers a signature check."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._return_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_stripe.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('redirect')
        url = self._build_url(StripeController._webhook_url)
        with patch(
            'odoo.addons.payment_stripe.controllers.main.StripeController._verify_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)
