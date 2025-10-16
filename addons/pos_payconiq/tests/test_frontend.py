import json
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from requests import Response

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.pos_payconiq.tests.payconiq_setup import TestPayconiq


# Keep the tour running even if an RPC error is raised
# e.g. we mock an error response from Payconiq API when creating a payment
def error_checker_payconiq_failed_rpc_request(message):
    return "RPC_ERROR" not in message


@tagged("post_install", "-at_install")
class TestFrontend(TestPayconiq):

    def test_payconiq_failed_to_create_payment(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with (self.mock_payconiq_call(post_status_code=401), mute_logger("odoo.http"), mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors")):
            self.start_pos_tour("payconiq_failed_to_create_payment", error_checker=error_checker_payconiq_failed_rpc_request)

    def test_payconiq_can_send_request(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_payconiq_call():
            self.start_pos_tour("payconiq_can_send_request")

    def test_payconiq_show_qr_code(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_payconiq_call():
            self.start_pos_tour("payconiq_show_qr_code")

    def test_payconiq_success_payment(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_payconiq_call():
            self.start_pos_tour("payconiq_success_payment")

    def test_payconiq_failed_payment(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_payconiq_call(), mute_logger("odoo.http"), mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors"):
            self.start_pos_tour("payconiq_failed_payment")

    def test_payconiq_failed_to_cancel_payment_error_422(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_payconiq_call(delete_status_code=422), mute_logger("odoo.http"), mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors"):
            self.start_pos_tour("payconiq_failed_to_cancel_payment_error_422")

    def test_payconiq_failed_to_cancel_payment_error_429(self):
        # It could be any other error code different than 422
        self.main_pos_config.with_user(self.pos_user).open_ui()
        with self.mock_payconiq_call(delete_status_code=429), mute_logger("odoo.http"), mute_logger("odoo.addons.pos_payconiq.utils.payconiq_errors"):
            self.start_pos_tour("payconiq_failed_to_cancel_payment_error_429")

    @contextmanager
    def mock_payconiq_call(self, is_sticker=False, post_status_code=200, delete_status_code=200):
        def mock_post(url, **kwargs):
            response = Response()

            if (not is_sticker and "merchant.api.preprod.bancontact.net/v3/payments" not in url) or \
               (is_sticker and "merchant.api.preprod.bancontact.net/v3/payments/pos" not in url):
                response.status_code = 404
                return response

            if 200 <= post_status_code < 300:
                payment_id = "payconiq_" + str(uuid.uuid4())
                response._content = json.dumps(
                    {
                        "paymentId": payment_id,
                        "_links": {"qrcode": {"href": "https://example.com/payconiq_qrcode"}},
                    },
                ).encode()

            response.status_code = post_status_code
            return response

        def mock_delete(url, **kwargs):
            response = Response()
            if "merchant.api.preprod.bancontact.net/v3/payments/" not in url:
                response.status_code = 404
                return response

            response.status_code = delete_status_code
            return response

        with (patch("odoo.addons.pos_payconiq.models.pos_payment_method.requests.post", mock_post),
              patch("odoo.addons.pos_payconiq.models.pos_payment_method.requests.delete", mock_delete),
              patch("odoo.addons.pos_payconiq.controllers.payconiq_controller.PayconiqController._verify_payconiq_signature")
                as mock_verify_signature):
            mock_verify_signature.return_value = self.payment_method_sticker_1.payconiq_ppid if is_sticker else self.payment_method_display.payconiq_ppid
            yield
