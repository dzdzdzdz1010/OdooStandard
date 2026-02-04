# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mollie.controllers.main import MollieController
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged('post_install', '-at_install')
class MollieTest(MollieCommon, PaymentHttpCommon):

    def test_payment_request_payload_values(self):
        tx = self._create_transaction(flow='redirect')

        payload = tx._mollie_prepare_payment_request_payload()
        expected_billing_address = {
            'givenName': 'Test',
            'familyName': 'User',
            'streetAndNumber': '',
            'postalCode': False,
            'city': False,
            'country': False,
            'email': 'test@example.com',
        }

        self.assertDictEqual(payload['amount'], {'currency': 'EUR', 'value': '1111.11'})
        self.assertDictEqual(payload['billingAddress'], expected_billing_address)
        self.assertDictEqual(payload['lines'][0]['totalAmount'], {'currency': 'EUR', 'value': '1111.11'})
        self.assertEqual(payload['description'], tx.reference)

    @mute_logger(
        'odoo.addons.payment_mollie.controllers.main',
        'odoo.addons.payment_mollie.models.payment_transaction',
    )
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(MollieController._webhook_url)
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={
                'status': 'paid',
                'amount': {'value': str(self.amount), 'currency': self.currency.name},
            },
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(tx.state, 'done')

    def test_payload_preparation_in_payment_with_tokenize(self):
        """
        When a payment is marked for tokenization and the partner already has
        a Mollie customer ID, the payload should be prepared as a *first* payment.

        - sequenceType must be 'first'
        - customerId must be set from the partner
        - mandateId must NOT be sent yet
        """
        self.tx.tokenize = True
        self.partner.mollie_customer_id = 'cst_test987'

        payload = self.tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'first')
        self.assertEqual(payload.get('customerId'), 'cst_test987')
        self.assertNotIn('mandateId', payload)

    def test_payload_preparation_in_payment_with_token(self):
        """
        When a payment is linked to an existing token (mandate),
        the payload should be prepared as a *recurring* payment.

        - sequenceType must be 'recurring'
        - customerId must be set from the partner
        - mandateId must be set from the token
        - payment method must NOT be explicitly provided
        """
        token = self.env['payment.token'].create({
            'provider_id': self.provider.id,
            'partner_id': self.partner.id,
            'provider_ref': 'mdt_test987',
            'payment_method_id': self.payment_method.id,
        })
        self.tx.token_id = token
        self.partner.mollie_customer_id = 'cst_test987'

        payload = self.tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'recurring')
        self.assertEqual(payload.get('customerId'), 'cst_test987')
        self.assertEqual(payload.get('mandateId'), 'mdt_test987')
        self.assertNotIn('method', payload)

    def test_payload_preparation_in_oneoff_payment(self):
        """
        When no tokenization is requested and no token is present,
        the payload should represent a one-off payment.

        - sequenceType must be 'oneoff'
        """
        payload = self.tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'oneoff')

    def test_api_call_to_fetch_customer_id(self):
        """
        When tokenization is enabled and the partner has no Mollie customer ID,
        the provider API should be called to create/fetch a customer.

        - sequenceType must be 'first'
        - customerId must come from the API response
        """
        self.tx.tokenize = True
        self.partner.mollie_customer_id = False

        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={'id': 'cst_test123'},
        ):
            payload = self.tx._mollie_prepare_payment_request_payload()

        self.assertEqual(payload.get('sequenceType'), 'first')
        self.assertEqual(payload.get('customerId'), 'cst_test123')
