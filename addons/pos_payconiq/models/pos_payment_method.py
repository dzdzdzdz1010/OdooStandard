import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_payconiq import const
from odoo.addons.pos_payconiq.utils.payconiq_errors import assert_payconiq_http_success


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # ----- Fields ----- #
    def _get_external_qr_provider_selection(self):
        return super()._get_external_qr_provider_selection() + [("payconiq", "Payconiq")]

    payconiq_api_key = fields.Char("Payconiq API Key")
    payconiq_ppid = fields.Char("Payconiq PPID")
    payconiq_test_mode = fields.Boolean(help="Run transactions in the test environment.")
    payconiq_usage = fields.Selection(
        selection=[
            ("display", "On-Screen Display"),
            ("sticker", "Static Sticker"),
        ],
        string="QR Usage",
        default="display",
        required=True,
        help=(
            "Defines how the QR Code is presented to the customer:\n"
            "- On-Screen Display: A new QR code is dynamically shown on the screen for each order.\n"
            "- Static Sticker: A fixed QR sticker placed near the counter is used for scanning with every order."
        ),
    )
    payconiq_sticker_size = fields.Selection(
        selection=[
            ("S", "Small (180x180)"),
            ("M", "Medium (250x250)"),
            ("L", "Large (400x400)"),
            ("XL", "Extra Large (800x800)"),
        ],
        string="Sticker Size",
        required=True,
        default="S",
    )
    payconiq_sticker_url = fields.Char("Sticker URL", compute="_compute_payconiq_sticker_url", store=True)

    # ----- Model ----- #
    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["payconiq_usage"]

    @api.depends("payment_provider", "payconiq_sticker_size", "payconiq_ppid", "payconiq_test_mode")
    def _compute_payconiq_sticker_url(self):
        for record in self:
            if (record.payment_provider != "payconiq" or record.payconiq_usage != "sticker"):
                record.payconiq_sticker_url = ""
                continue
            record.payconiq_sticker_url = record._get_payconiq_api_url("qrcode") % (
                record.payconiq_sticker_size,
                record.payconiq_ppid,
                record.id,
            )

    @api.constrains("payment_provider", "journal_id", "company_id")
    def _check_payconiq_currency(self):
        """
        Ensure that Payconiq payment methods use a supported currency.
        """
        for record in self:
            if record.payment_provider != "payconiq":
                continue

            currency = record.journal_id.currency_id or record.company_id.currency_id
            if currency.name not in const.SUPPORTED_CURRENCIES:
                raise ValidationError(
                    record.env._(
                        "Payconiq only supports the following currencies: %s.\n"
                        "Please make sure the journal uses one of them.",
                    )
                    % ", ".join(const.SUPPORTED_CURRENCIES),
                )

    @api.constrains("payment_provider", "payconiq_usage", "config_ids")
    def _check_payconiq_sticker_one_pos_config(self):
        for record in self:
            if (
                record.payment_provider == "payconiq"
                and record.payconiq_usage == "sticker"
                and len(record.config_ids) > 1
            ):
                raise ValidationError(
                    _("You must assign only one POS configuration to this payment method if you want to use the QR Sticker from Payconiq."),
                )

    def download_payconiq_sticker(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.payconiq_sticker_url,
            "target": "download",
        }

    # ----- Payconiq Integration ----- #
    def create_payconiq_payment(self, payment_id, **kwargs):
        pos_payment = self.env["pos.payment"].search([("id", "=", payment_id)], limit=1)

        if not pos_payment.exists():
            raise ValidationError(_("Payconiq payment not found."))

        if not pos_payment.payconiq_id or pos_payment.payment_status not in ["waiting", "waitingScan", "waitingCancel"]:
            headers = {
                "Authorization": f"Bearer {self.payconiq_api_key}",
                "Content-Type": "application/json",
            }
            url, payload = self._prepare_payconiq_payment_request(**kwargs)
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            assert_payconiq_http_success(response)
            payconiq_data = response.json()

            pos_payment.payconiq_id = payconiq_data["paymentId"]
            qr_code = payconiq_data.get("_links", {}).get("qrcode", {}).get("href", "")
            if qr_code:
                qr_code += "&s=XL"
            pos_payment.qr_code = qr_code

        return {
            "pos.payment": pos_payment._load_pos_data_read(
                pos_payment,
                pos_payment.pos_order_id.config_id,
            ),
        }

    def cancel_payconiq_payment(self, payment_id, force_cancel=False):
        pos_payment = self.env["pos.payment"].search([("id", "=", payment_id)], limit=1)
        if not pos_payment.exists():
            raise ValidationError(_("Payconiq payment not found."))

        payconiq_id = pos_payment.payconiq_id
        if payconiq_id:
            url = f"{self._get_payconiq_api_url()}/v3/payments/{payconiq_id}"
            headers = {
                "Authorization": f"Bearer {self.payconiq_api_key}",
                "Content-Type": "application/json",
            }
            response = requests.delete(url, headers=headers, timeout=5)
            if not force_cancel:
                assert_payconiq_http_success(response,
                    {422: (_("Unable to cancel payment. The payment may not be in a cancellable state."), ValidationError)},
                )

        pos_payment.payconiq_id = False
        pos_payment.qr_code = False

        return {
            "pos.payment": pos_payment._load_pos_data_read(
                pos_payment,
                pos_payment.pos_order_id.config_id,
            ),
        }

    # ----- Helpers ----- #
    def _get_callback_url(self):
        """
        Construct the callback URL for Payconiq to send payment status updates.
        """
        url = f"{self.get_base_url()}/webhook/payconiq"
        if self.payconiq_test_mode:
            url += "?mode=test"
        return url

    def _prepare_payconiq_payment_request(self, **kwargs):
        """
        Wrapper to prepare the appropriate Payconiq payment request.
        """
        usage = kwargs.get("usage")
        if usage == "sticker":
            return self._prepare_sticker_payment_request(**kwargs)
        return self._prepare_display_payment_request(**kwargs)

    def _prepare_display_payment_request(self, **kwargs):
        """
        Prepare the payload for creating a Payconiq payment for a on display QR code.
        https://docs.payconiq.be/apis/merchant-payment.openapi/merchant-endpoints/create

        Field notes:
            - `amount`: Payconiq expects the amount in cents (integer), so we multiply the float by 100.
            - `callbackUrl`: Endpoint that receives Payconiq's payment status updates.
        """
        callback_url = self._get_callback_url()
        return [
            f"{self._get_payconiq_api_url()}/v3/payments",
            {
                "amount": round(kwargs.get("amount", 0.0) * 100),
                "currency": kwargs.get("currency", "EUR"),
                "description": kwargs.get("description", "")[:140],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _prepare_sticker_payment_request(self, **kwargs):
        """
        Prepare the payload for creating a Payconiq payment for a static QR (sticker)
        https://docs.payconiq.be/apis/merchant-payment.openapi/merchant-endpoints/create_static_qr_payment

        Field notes:
            - `amount`: Payconiq expects the amount in cents (integer), so we multiply the float by 100.
            - `posId`: We use the payment method ID here instead of the POS config ID
            because each Payconiq sticker is tied to a unique Payconiq POS entity.
            By creating one payment method per sticker, we can support multiple stickers
            under the same POS config.
            - `shopId`: Based on the POS config ID, representing the shop as defined in Odoo.
            - `shopName`: Human-readable name of the POS, shown to the customer.
            - `callbackUrl`: Endpoint that receives Payconiq's payment status updates.
        """
        callback_url = self._get_callback_url()
        return [
            f"{self._get_payconiq_api_url()}/v3/payments/pos",
            {
                "amount": round(kwargs.get("amount", 0.0) * 100),
                "currency": kwargs.get("currency", "EUR"),
                "description": kwargs.get("description", "")[:140],
                "posId": f'pm{kwargs.get("paymentMethodId", "")}'[:36],
                "shopId": f'pos{kwargs.get("posId", "")}'[:36],
                "shopName": kwargs.get("shopName", "")[:36],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _get_payconiq_api_url(self, target="merchant"):
        environment = "preprod" if self.payconiq_test_mode else "production"
        return const.API_URLS[environment][target]
