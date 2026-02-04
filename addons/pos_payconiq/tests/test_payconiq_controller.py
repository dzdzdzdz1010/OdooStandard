import json
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestController(CommonPosTest, TestPointOfSaleHttpCommon):

    def setUp(self):
        super().setUp()
        self.test_ppid = "test_payconiq_ppid"
        self.web_hook_payload_base = {"transferAmount": 100, "amount": 100, "currency": "EUR"}

        self.payconiq_payment_method = self.env['pos.payment.method'].create({
            'name': 'Payconiq',
            'payconiq_ppid': self.test_ppid,
            'journal_id': self.company_data['default_journal_bank'].id,
            'receivable_account_id': self.company_data['default_account_receivable'].id,
        })

        self.pos_config_usd.write({
            'payment_method_ids': [(4, self.payconiq_payment_method.id, 0)],
        })

    def test_payconiq_webhook_payment_status_done(self):
        pos_payment, payload = self._make_payment_and_payload()

        with self._notify_patcher(pos_payment) as mock_notify:
            self._post_and_assert_status(pos_payment, payload, "SUCCEEDED", "done")
            self._assert_notify_called_once(mock_notify, pos_payment, "SUCCEEDED")

    def test_payconiq_webhook_payment_status_done_ignore(self):
        pos_payment, payload = self._make_payment_and_payload()
        pos_payment.payment_status = "done"

        with self._notify_patcher(pos_payment) as mock_notify:
            for status in ("SUCCEEDED", "CANCELLED"):
                self._post_status(payload, status)
                self.assertEqual(pos_payment.payment_status, "done")

            mock_notify.assert_not_called()

    def test_payconiq_webhook_payment_status_error(self):
        # all of these should end up in retry + notify(status)
        for payconiq_status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
            pos_payment, payload = self._make_payment_and_payload()
            self.assertEqual(pos_payment.payment_status, "waitingScan")

            with self._notify_patcher(pos_payment) as mock_notify:
                self._post_and_assert_status(pos_payment, payload, payconiq_status, "retry")
                self._assert_notify_called_once(mock_notify, pos_payment, payconiq_status)

    def test_payconiq_webhook_payment_status_error_ignore(self):
        pos_payment, payload = self._make_payment_and_payload()
        pos_payment.payment_status = "retry"

        with self._notify_patcher(pos_payment) as mock_notify:
            for status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
                self._post_status(payload, status)
                self.assertEqual(pos_payment.payment_status, "retry")

            mock_notify.assert_not_called()

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_payconiq_webhook_payment_not_found(self):
        webhook_payload = {
            "paymentId": 999999,
            "transferAmount": 100,
            "tippingAmount": 0,
            "amount": 100,
            "totalAmount": 100,
            "description": "Sample description",
            "status": "SUCCEEDED",
            "debtor": {"name": "John", "iban": "*************12636"},
            "currency": "EUR",
        }

        response = self._post_payconiq_webhook(webhook_payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, "Payment not found.")

    def _make_payment_and_payload(self, payconiq_id="123456"):
        pos_payment = self._init_payconiq_pos_payment(payconiq_id)
        payload = dict(self.web_hook_payload_base, paymentId=payconiq_id)
        return pos_payment, payload

    def _notify_patcher(self, pos_payment):
        return patch.object(pos_payment.pos_order_id.config_id.__class__, "_notify")

    def _assert_notify_called_once(self, mock_notify, pos_payment, payconiq_status):
        mock_notify.assert_called_once_with(
            "PAYCONIQ_PAYMENTS_NOTIFICATION",
            {
                "order_id": pos_payment.pos_order_id.id,
                "payment_id": pos_payment.id,
                "payconiq_status": payconiq_status,
            },
        )

    def _init_payconiq_pos_payment(self, payconiq_id):
        order, _ = self.create_backend_pos_order(
            {
                "line_data": [
                    {"product_id": self.ten_dollars_no_tax.product_variant_id.id},
                ],
            },
        )
        return self.env["pos.payment"].create(
            {
                "amount": 100,
                "payment_status": "waitingScan",
                "payconiq_id": payconiq_id,
                "payment_method_id": self.payconiq_payment_method.id,
                "pos_order_id": order.id,
            },
        )

    def _post_payconiq_webhook(self, payload, signature_valid=True):
        with patch("odoo.addons.pos_payconiq.controllers.payconiq_controller.PayconiqController._verify_payconiq_signature") as mock_verify_signature:
            mock_verify_signature.return_value = self.test_ppid if signature_valid else ""

            return self.url_open(
                "/webhook/payconiq",
                data=json.dumps(payload),
                headers={"content-type": "application/json"},
                method="POST",
            )

    def _post_status(self, payload, status):
        payload["status"] = status
        response = self._post_payconiq_webhook(payload)
        self.assertEqual(response.status_code, 200)
        return response

    def _post_and_assert_status(self, pos_payment, payload, status, expected_payment_status):
        self._post_status(payload, status)
        self.assertEqual(pos_payment.payment_status, expected_payment_status)
