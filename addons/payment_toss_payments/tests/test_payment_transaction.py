from odoo.tests import tagged

from odoo.addons.payment_toss_payments.tests.common import TossPaymentsCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(TossPaymentsCommon):
    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be made of alphanumeric and symbols '-' and '_'."""
        reference = self.env['payment.transaction']._compute_reference(
            provider_code='toss_payments'
        )

        self.assertTrue(reference)
        pattern = r'^[a-zA-Z0-9_-]+$'
        self.assertRegex(reference, pattern)

    def test_reference_length_is_between_6_and_64_chars(self):
        """The computed reference must be between 6 and 64 characters, both numbers inclusive."""
        reference = self.env['payment.transaction']._compute_reference(
            provider_code='toss_payments'
        )
        self.assertTrue(6 <= len(reference) <= 64)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction('direct')
        amount_data = tx._extract_amount_data(self.payment_result_data)
        self.assertDictEqual(
            amount_data, {'amount': self.amount, 'currency_code': self.currency_krw.name}
        )

    def test_apply_updates_sets_payment_method(self):
        """Test that the transaction state is set to 'done', paymentKey and secret updated
        according to the payment data on successful payment."""
        tx = self._create_transaction('direct')

        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, self.payment_result_data['paymentKey'])
        self.assertEqual(tx.toss_payments_payment_secret, self.payment_result_data['secret'])
