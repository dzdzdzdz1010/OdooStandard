from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_toss_payments.controllers.main import TossPaymentsController
from odoo.addons.payment_toss_payments.tests.common import TossPaymentsCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(TossPaymentsCommon, PaymentHttpCommon):
    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_initiating_payment_triggers_api_request(self):
        """Test receiving a valid redirect request triggers the processing of the payment data."""
        tx = self._create_transaction('direct')
        redirect_success_params = {'orderId': tx.reference, "paymentKey": "test-pk", "amount": 750}
        url = self._build_url(TossPaymentsController._success_url)
        with (
            patch('odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._send_api_request'
            ) as process_mock,
        ):
            self._make_http_get_request(url, params=redirect_success_params)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_webhook_triggers_apply_updates(self):
        """Test receiving a valid webhook notification triggers the processing of the payment
        data."""
        self._create_transaction('direct')
        url = self._build_url(TossPaymentsController._webhook_url)
        with (
            patch(
                'odoo.addons.payment_toss_payments.controllers.main.TossPaymentsController._verify_signature'
            ),
            patch(
                'odoo.addons.payment_toss_payments.models.payment_transaction.PaymentTransaction._apply_updates'
            ) as apply_updates_mock,
        ):
            self._make_json_request(url, data=self.webhook_data)
        self.assertEqual(apply_updates_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_webhook_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction('direct')
        url = self._build_url(TossPaymentsController._webhook_url)
        with (
            patch(
                'odoo.addons.payment_toss_payments.controllers.main.TossPaymentsController._verify_signature'
            ) as signature_check_mock,
            patch(
                'odoo.addons.payment_toss_payments.models.payment_transaction.PaymentTransaction._apply_updates'
            ),
        ):
            self._make_json_request(url, data=self.webhook_data)
        self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """Test the verification of a notification with a valid signature."""
        tx = self._create_transaction('direct')
        tx.write({'toss_payments_payment_secret': 'test-secret'})
        self._assert_does_not_raise(
            Forbidden, TossPaymentsController._verify_signature, tx, self.webhook_data['data']
        )

    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """Test the verification of a notification with a missing signature."""
        tx = self._create_transaction('direct')
        tx.write({'toss_payments_payment_secret': 'test-secret'})
        webhook_data = dict(self.webhook_data['data'], status='DONE', secret=None)
        self.assertRaises(Forbidden, TossPaymentsController._verify_signature, tx, webhook_data)

    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """Test the verification of a notification with an invalid signature."""
        tx = self._create_transaction('direct')
        tx.write({'toss_payments_payment_secret': 'test-secret'})
        webhook_data = dict(self.webhook_data['data'], status='DONE', secret='dummy')
        self.assertRaises(Forbidden, TossPaymentsController._verify_signature, tx, webhook_data)

    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_handle_fail_sets_error_and_redirects(self):
        """Test that hitting the fail redirect endpoint sets the transaction to error."""
        tx = self._create_transaction('direct')
        url = self._build_url(TossPaymentsController._fail_url)
        error_data = {'code': 'ERR', 'message': 'Payment refused', 'orderId': tx.reference}
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._set_error'
        ) as set_error_mock:
            self._make_http_get_request(url, params=error_data)
        self.assertEqual(set_error_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_toss_payments.controllers.main')
    def test_success_flow_api_validation_error_triggers_set_error(self):
        """If sending the confirm API request raises ValidationError, the tx must be set to
        error."""
        tx = self._create_transaction('direct')
        redirect_success_params = {'orderId': tx.reference, "paymentKey": "test-pk", "amount": 750}
        url = self._build_url(TossPaymentsController._success_url)
        with (
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._validate_amount'
            ),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._send_api_request',
                side_effect=ValidationError('invalid amount'),
            ),
            patch(
                'odoo.addons.payment.models.payment_transaction.PaymentTransaction._set_error'
            ) as set_error_mock,
        ):
            self._make_http_get_request(url, params=redirect_success_params)
        self.assertEqual(set_error_mock.call_count, 1)
