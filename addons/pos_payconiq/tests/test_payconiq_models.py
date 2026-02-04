import json
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from requests import Response

from odoo import Command
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.pos_payconiq import const
from odoo.addons.pos_payconiq.tests.payconiq_setup import TestPayconiq


@tagged("post_install", "-at_install")
class TestModels(TestPayconiq, CommonPosTest):

    # --------------------------
    # Currency
    # --------------------------
    def test_journal_supported_currency(self):
        ### Company EUR ###
        # EUR --> USD
        with self.assertRaises(ValidationError):
            self.payconiq_journal.currency_id = self.usd_currency
        # EUR -> False
        self.payconiq_journal.currency_id = False
        # False -> USD
        with self.assertRaises(ValidationError):
            self.payconiq_journal.currency_id = self.usd_currency
        # False -> EUR
        self.payconiq_journal.currency_id = self.eur_currency

        ### Company USD ###
        self.company.currency_id = self.usd_currency
        # EUR --> False
        with self.assertRaises(ValidationError):
            self.payconiq_journal.currency_id = False
        # EUR --> USD
        with self.assertRaises(ValidationError):
            self.payconiq_journal.currency_id = self.usd_currency

    def test_payment_method_supported_currency(self):
        usd_journal = self.env["account.journal"].create({
            "name": "USD Journal",
            "code": "USDJOURNAL",
            "type": "bank",
            "company_id": self.company.id,
            "currency_id": self.usd_currency.id,
        })

        # False --> USD Journal
        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.journal_id = usd_journal

        # False --> EUR Journal
        self.payment_method_sticker_1.journal_id = self.payconiq_journal

        # EUR journal --> USD Journal
        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.journal_id = usd_journal

    def test_company_supported_currency(self):
        ### Journal EUR ###
        # EUR --> USD
        self.company.currency_id = self.usd_currency
        # USD --> EUR
        self.company.currency_id = self.eur_currency

        ### Journal False ###
        self.payconiq_journal.currency_id = False
        # EUR --> USD
        with self.assertRaises(ValidationError):
            self.company.currency_id = self.usd_currency

    # --------------------------
    # Payment Methods
    # --------------------------
    def test_default_payment_methods(self):
        default_methods = self.env['pos.config']._default_payment_methods()
        payconiq_methods = [method for method in default_methods if method.payment_provider == 'payconiq']

        # Has display methods
        display_methods = [method for method in payconiq_methods if method.payconiq_usage == 'display']
        self.assertEqual(len(display_methods), 1)

        # No sticker methods
        sticker_methods = [method for method in payconiq_methods if method.payconiq_usage == 'sticker']
        self.assertEqual(len(sticker_methods), 0)

    def test_one_payconiq_sticker_per_pos_config(self):
        test_config = self.env["pos.config"].create(
            {
                "name": "Test POS Config",
                "module_pos_restaurant": False,
            },
        )
        payment_method_sticker_3 = self.env["pos.payment.method"].create(
            {
                "name": "Payconiq - Sticker 3",
                "payment_method_type": "external_qr",
                "payment_provider": "payconiq",
                "payconiq_usage": "sticker",
                "payconiq_sticker_size": "L",
                "company_id": self.company.id,
                "journal_id": self.payconiq_journal.id,
                "payconiq_api_key": "sticker_api_key",
                "payconiq_ppid": "sticker_profile_id",
            },
        )

        # Assigning sticker already assigned to another POS config via pos.payment.method
        with self.assertRaises(ValidationError):
            self.payment_method_sticker_1.config_ids = [Command.link(test_config.id)]

        # Assigning sticker already assigned to another POS config via pos.config
        payment_method_sticker_3.config_ids = [Command.clear()]
        with self.assertRaises(ValidationError):
            test_config.payment_method_ids = [Command.link(self.payment_method_sticker_1.id)]

        # Assigning a new sticker to the POS config should work
        test_config.payment_method_ids = [Command.link(payment_method_sticker_3.id)]

    # --------------------------------------
    # Create Payconiq Payment
    # --------------------------------------
    def test_create_payconiq_payment_not_found(self):
        with (self.assertRaises(ValidationError)):
            self.payment_method_display.create_payconiq_payment(payment_id=9999)

    def test_create_payconiq_payment_success(self):
        payment = self._init_payconiq_pos_payment()
        generated_payconiq_id = self._generate_payconiq_id()
        generated_qr_code = self._generate_qr_code()

        with self.mock_payconiq_call(payconiq_id=generated_payconiq_id, qr_code=generated_qr_code), mute_logger("odoo.tools.translate"):
            result = payment.payment_method_id.create_payconiq_payment(payment.id)

            self.assertEqual(len(result["pos.payment"]), 1)
            self.assertEqual(result["pos.payment"][0]["id"], payment.id)
            self.assertEqual(payment.payconiq_id, generated_payconiq_id)
            self.assertEqual(payment.qr_code, generated_qr_code + "&s=XL")

    def test_create_payconiq_payment_already_exists_not_processing(self):
        existing_payconiq_id = "__payconiq_existing_id__"
        existing_qr_code = "__payconiq_existing_qr_code__"
        payment = self._init_payconiq_pos_payment(
            payconiq_id=existing_payconiq_id,
            qr_code=existing_qr_code,
            payment_status="retry",
        )

        generated_payconiq_id = self._generate_payconiq_id()
        generated_qr_code = self._generate_qr_code()

        with self.mock_payconiq_call(payconiq_id=generated_payconiq_id, qr_code=generated_qr_code), mute_logger("odoo.tools.translate"):
            result = payment.payment_method_id.create_payconiq_payment(payment.id)

            self.assertEqual(len(result["pos.payment"]), 1)
            self.assertEqual(result["pos.payment"][0]["id"], payment.id)
            self.assertEqual(payment.payconiq_id, generated_payconiq_id)
            self.assertEqual(payment.qr_code, generated_qr_code + "&s=XL")

    def test_create_payconiq_payment_already_exists_processing(self):
        existing_payconiq_id = "__payconiq_existing_id__"
        existing_qr_code = "__payconiq_existing_qr_code__"
        payment = self._init_payconiq_pos_payment(
            payconiq_id=existing_payconiq_id,
            qr_code=existing_qr_code,
            payment_status="waitingScan",
        )

        generated_payconiq_id = self._generate_payconiq_id()
        generated_qr_code = self._generate_qr_code()

        with self.mock_payconiq_call(payconiq_id=generated_payconiq_id, qr_code=generated_qr_code):
            result = payment.payment_method_id.create_payconiq_payment(payment.id)

            self.assertEqual(len(result["pos.payment"]), 1)
            self.assertEqual(result["pos.payment"][0]["id"], payment.id)
            self.assertEqual(payment.payconiq_id, existing_payconiq_id)
            self.assertEqual(payment.qr_code, existing_qr_code)

    def test_create_payconiq_payment_api_error(self):
        codes = [(400, MissingError), (401, AccessDenied), (403, AccessDenied),
                 (404, UserError), (422, ValidationError), (429, AccessDenied),
                 (500, AccessError), (503, AccessError)]

        payment = self._init_payconiq_pos_payment()
        for status_code, expected_exception in codes:

            with self.mock_payconiq_call(post_status_code=status_code), \
                mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors"), \
                mute_logger("odoo.tools.translate"), \
                self.assertRaises(expected_exception):
                payment.payment_method_id.create_payconiq_payment(payment.id)

    # --------------------------------------
    # Cancel Payconiq Payment
    # --------------------------------------
    def test_cancel_payconiq_payment_not_found(self):
        with (self.assertRaises(ValidationError)):
            self.payment_method_display.cancel_payconiq_payment(payment_id=9999)

    def test_cancel_payconiq_payment_success(self):
        payconiq_id = self._generate_payconiq_id()
        qr_code = self._generate_qr_code()
        payment = self._init_payconiq_pos_payment(payconiq_id=payconiq_id, qr_code=qr_code, payment_status="waitingScan")
        with self.mock_payconiq_call(), mute_logger("odoo.tools.translate"):
            result = payment.payment_method_id.cancel_payconiq_payment(payment.id)

            self.assertEqual(len(result["pos.payment"]), 1)
            self.assertEqual(result["pos.payment"][0]["id"], payment.id)
            self.assertFalse(payment.payconiq_id)
            self.assertFalse(payment.qr_code)

    def test_cancel_payconiq_payment_no_payconiq_id(self):
        payment = self._init_payconiq_pos_payment(payment_status="waitingScan")
        with self.mock_payconiq_call():
            result = payment.payment_method_id.cancel_payconiq_payment(payment.id)

            self.assertEqual(len(result["pos.payment"]), 1)
            self.assertEqual(result["pos.payment"][0]["id"], payment.id)
            self.assertFalse(payment.payconiq_id)
            self.assertFalse(payment.qr_code)

    def test_cancel_payconiq_payment_api_error(self):
        codes = [(400, MissingError), (401, AccessDenied), (403, AccessDenied),
                 (404, UserError), (422, ValidationError), (429, AccessDenied),
                 (500, AccessError), (503, AccessError)]

        payconiq_id = self._generate_payconiq_id()
        qr_code = self._generate_qr_code()
        payment = self._init_payconiq_pos_payment(payconiq_id=payconiq_id, qr_code=qr_code, payment_status="waitingScan")

        for status_code, expected_exception in codes:

            with self.mock_payconiq_call(delete_status_code=status_code), \
                mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors"), \
                mute_logger("odoo.tools.translate"), \
                self.assertRaises(expected_exception):
                payment.payment_method_id.cancel_payconiq_payment(payment.id)

    def test_cancel_payconiq_payment_api_error_force_cancel(self):
        payconiq_id = self._generate_payconiq_id()
        qr_code = self._generate_qr_code()
        payment = self._init_payconiq_pos_payment(payconiq_id=payconiq_id, qr_code=qr_code, payment_status="waitingScan")

        with self.mock_payconiq_call(delete_status_code=400), \
            mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors"):
            result = payment.payment_method_id.cancel_payconiq_payment(payment.id, force_cancel=True)

            self.assertEqual(len(result["pos.payment"]), 1)
            self.assertEqual(result["pos.payment"][0]["id"], payment.id)
            self.assertFalse(payment.payconiq_id)
            self.assertFalse(payment.qr_code)

    # --------------------------------------
    # Prepare Payconiq Payment Request
    # --------------------------------------
    def test_prepare_display_payment_request(self):
        actual = self.payment_method_display._prepare_display_payment_request(
            amount=10.00,
            currency="EUR",
            description="sample description",
        )
        expected = [
            f"{const.API_URLS['preprod']['merchant']}/v3/payments",
            {
                "amount": 1000,
                "currency": "EUR",
                "description": "sample description",
                "identifyCallbackUrl": f"{self.payment_method_sticker_1.get_base_url()}/webhook/payconiq?mode=test",
                "callbackUrl": f"{self.payment_method_sticker_1.get_base_url()}/webhook/payconiq?mode=test",
            },
        ]
        self.assertEqual(actual, expected)

    def test_prepare_sticker_payment_request(self):
        actual = self.payment_method_sticker_1._prepare_sticker_payment_request(
            amount=10.00,
            currency="EUR",
            description="sample description",
            paymentMethodId=1,
            posId=2,
            shopName="Shop Name",
        )
        expected = [
            f"{const.API_URLS['preprod']['merchant']}/v3/payments/pos",
            {
                "amount": 1000,
                "currency": "EUR",
                "description": "sample description",
                "identifyCallbackUrl": f"{self.payment_method_sticker_1.get_base_url()}/webhook/payconiq?mode=test",
                "callbackUrl": f"{self.payment_method_sticker_1.get_base_url()}/webhook/payconiq?mode=test",
                "posId": "pm1",
                "shopId": "pos2",
                "shopName": "Shop Name",
            },
        ]
        self.assertEqual(actual, expected)

    # --------------------------------------
    # Helpers
    # --------------------------------------
    @contextmanager
    def mock_payconiq_call(self, payconiq_id=None, qr_code=None, post_status_code=200, delete_status_code=200):
        def mock_post(url, **kwargs):
            response = Response()

            if 200 <= post_status_code < 300:
                payment_id = payconiq_id or self._generate_payconiq_id()
                href = qr_code or self._generate_qr_code()
                response._content = json.dumps(
                    {
                        "paymentId": payment_id,
                        "_links": {"qrcode": {"href": href}},
                    },
                ).encode()

            response.status_code = post_status_code
            return response

        def mock_delete(url, **kwargs):
            response = Response()
            response.status_code = delete_status_code
            return response

        with (patch("odoo.addons.pos_payconiq.models.pos_payment_method.requests.post", mock_post),
              patch("odoo.addons.pos_payconiq.models.pos_payment_method.requests.delete", mock_delete)):
            yield

    def _generate_payconiq_id(self):
        return "payconiq_" + str(uuid.uuid4())

    def _generate_qr_code(self):
        return "https://example.com/payconiq_qrcode/" + str(uuid.uuid4())

    def _init_payconiq_pos_payment(self, **kwargs):
        order, _ = self.create_backend_pos_order(
            {
                "pos_config": self.main_pos_config,
                "line_data": [
                    {"product_id": self.ten_dollars_no_tax.product_variant_id.id},
                ],
            },
        )
        return self.env["pos.payment"].create(
            {
                "amount": 100,
                "payment_status": "pending",
                "payment_method_id": self.payment_method_display.id,
                "pos_order_id": order.id,
                **kwargs,
            },
        )
