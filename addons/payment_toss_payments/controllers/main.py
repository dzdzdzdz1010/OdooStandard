import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_toss_payments import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class TossPaymentsController(http.Controller):
    _success_url = '/payment/toss-payments/success'
    _fail_url = '/payment/toss-payments/fail'
    _webhook_url = '/payment/toss-payments/webhook'

    @http.route(_success_url, type='http', auth='public')
    def _toss_payments_success_return(self, **data):
        """Process payment after validation from Toss SDK is successful.

        The method handles payment using Toss API.

        :param dict data: The dict data of successUrl's query parameter.
        Expected keys = ["orderId", "paymentKey", "amount"]
        """
        _logger.info("Handling redirection from Toss Payments with data:\n%s", pprint.pformat(data))
        tx_sudo = (
            request.env['payment.transaction'].sudo()._search_by_reference('toss_payments', data)
        )
        if not tx_sudo:
            return None

        # Need payment_data validation before sending payment confirmation request because the
        # amount data can be manipulated from the client side.
        tx_sudo._validate_amount({'totalAmount': data.get("amount")})
        if tx_sudo.state != 'error':  # Amount validation fails; should not send API request
            try:
                payment_data = tx_sudo._send_api_request('POST', '/v1/payments/confirm', json=data)
            except ValidationError as e:
                tx_sudo._set_error(e)
            else:
                tx_sudo._process('toss_payments', payment_data)

        return request.redirect('/payment/status')

    @http.route(_fail_url, type='http', auth='public')
    def _toss_payments_fail_return(self, **error_data):
        """Handle unsuccessful validation from Toss SDK.

        :param dict error_data: The dict data of successUrl's query parameter.
        Expected keys = ["code", "message", "orderId"]
        """
        _logger.info(
            "Handling redirection from Toss Payments with data:\n%s", pprint.pformat(error_data)
        )
        tx_sudo = (
            request.env['payment.transaction']
            .sudo()
            ._search_by_reference('toss_payments', error_data)
        )
        if not tx_sudo:
            return None

        message = f"{error_data.get('message')} ({error_data.get('code')})"
        tx_sudo._set_error(message)

        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def _toss_payments_webhook(self):
        """Process the notification data sent by Toss Payments to the webhook.

        Event message schema can be found in Toss Payments documentation:
        https://docs.tosspayments.com/reference/using-api/webhook-events#%EC%9D%B4%EB%B2%A4%ED%8A%B8-%EB%B3%B8%EB%AC%B8

        :param dict data: The event data.
        :return: The 'OK' string to acknowledge the notification.
        :rtype: str
        """
        request_data = request.get_json_data()
        _logger.info(
            "Notification received from Toss Payments with data:\n%s", pprint.pformat(request_data)
        )
        event_type = request_data.get('eventType')
        if event_type in const.HANDLED_WEBHOOK_EVENTS:
            payment_data = request_data.get('data')
            tx_sudo = (
                request.env['payment.transaction']
                .sudo()
                ._search_by_reference('toss_payments', payment_data)
            )
            if tx_sudo:
                self._verify_signature(tx_sudo, payment_data)
                tx_sudo._process('toss_payments', payment_data)

        return ''

    @staticmethod
    def _verify_signature(tx_sudo, payment_data):
        """Check that the received payment data's secret key matches the tx_sudo's secret key.

        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :param dict payment_data: The payment data.
        :return: None
        :raise Forbidden: If the payment secret keys don't match.
        """
        # Expired event might not have secret if we never initiated the payment flow. Also aborted
        # event has the secret, but our implementation would not capture the secret in the case of
        # API call validation error (See _toss_payments_success_return()). In these two cases, we
        # skip the verification.
        if payment_data.get('status') in const.VERIFICATION_EXEMPT_STATUSES:
            return

        received_signature = payment_data.get('secret')
        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden

        expected_signature = tx_sudo.toss_payments_payment_secret or ''
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden
