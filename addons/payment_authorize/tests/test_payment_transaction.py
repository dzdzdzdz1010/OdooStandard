# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(AuthorizeCommon):
    def test_search_by_reference_finds_transaction_by_reference_id(self):
        """Test that return from checkout finds transaction by referenceId."""
        tx = self._create_transaction('redirect')
        return_data = {'referenceId': tx.reference}
        found_tx = self.env['payment.transaction']._search_by_reference('authorize', return_data)
        self.assertEqual(found_tx, tx)

    def test_search_by_reference_finds_transaction_by_provider_reference(self):
        """Test that webhook search finds transaction by provider_reference."""
        tx = self._create_transaction('direct', provider_reference=self.trans_id)
        webhook_data = {
            'eventType': 'net.authorize.payment.authcapture.created',
            'payload': {'id': self.trans_id},
        }
        found_tx = self.env['payment.transaction']._search_by_reference('authorize', webhook_data)
        self.assertEqual(found_tx, tx)

    def test_apply_updates_processes_webhook_fraud_held(self):
        """Test that webhook fraud held event sets transaction to pending."""
        tx = self._create_transaction('direct', provider_reference=self.trans_id)
        tx._apply_updates(self.webhook_fraud_held_data)
        self.assertEqual(tx.state, 'pending')

    def test_apply_updates_processes_webhook_fraud_approved(self):
        """Test that webhook fraud approved event sets transaction to done."""
        tx = self._create_transaction('direct', state='pending', provider_reference=self.trans_id)
        tx._apply_updates(self.webhook_fraud_approved_data)
        self.assertEqual(tx.state, 'done')

    def test_apply_updates_processes_webhook_authcapture(self):
        """Test that webhook authcapture event sets transaction to done."""
        tx = self._create_transaction('direct', provider_reference=self.trans_id)
        tx._apply_updates(self.webhook_authcapture_data)
        self.assertEqual(tx.state, 'done')

    def test_apply_updates_processes_webhook_authorization(self):
        """Test that webhook authorization event sets transaction to authorized."""
        tx = self._create_transaction('direct', provider_reference=self.trans_id)
        webhook_data = {
            **self.webhook_notification_base,
            'eventType': 'net.authorize.payment.authorization.created',
            'payload': {
                **self.webhook_notification_base['payload'],
                'transactionType': 'authOnlyTransaction',
            },
        }
        tx._apply_updates(webhook_data)
        self.assertEqual(tx.state, 'authorized')

    def test_apply_updates_processes_webhook_fraud_declined(self):
        """Test that webhook fraud declined event sets transaction to canceled."""
        tx = self._create_transaction('direct', state='pending', provider_reference=self.trans_id)
        webhook_data = {
            **self.webhook_notification_base,
            'eventType': 'net.authorize.payment.fraud.declined',
            'payload': {**self.webhook_notification_base['payload'], 'responseCode': 2},
        }
        tx._apply_updates(webhook_data)
        self.assertEqual(tx.state, 'cancel')
