import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from requests import Response

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_payconiq import const


@tagged("post_install", "-at_install")
class TestSignature(CommonPosTest, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.utils = PayconiqTestUtils()

        # Generate test keys
        cls.private_key, cls.public_key = cls.utils.generate_ec_keypair()
        cls.kid = "test-kid-12345"
        cls.jwk = cls.utils.create_jwk(cls.public_key, cls.kid)

        cls.test_ppid = "test-ppid-123"
        cls.test_payconiq_id = "test-payconiq-id-123"

    def setUp(self):
        super().setUp()
        # Clear JWK cache before each test
        self.env["ir.config_parameter"].sudo().set_str("pos_payconiq.jwk_cache", None)

        self.payconiq_payment_method = self.env['pos.payment.method'].create({
            'name': 'Payconiq',
            'payconiq_ppid': self.test_ppid,
            'journal_id': self.company_data['default_journal_bank'].id,
            'receivable_account_id': self.company_data['default_account_receivable'].id,
        })

        self.pos_config_usd.write({
            'payment_method_ids': [(4, self.payconiq_payment_method.id, 0)],
        })

        order, _ = self.create_backend_pos_order(
            {
                "line_data": [
                    {"product_id": self.ten_dollars_no_tax.product_variant_id.id},
                ],
            },
        )
        self.payconiq_order = order

        self.payconiq_payment = self.env["pos.payment"].create(
            {
                "amount": 100,
                "payment_status": "waitingScan",
                "payconiq_id": self.test_payconiq_id,
                "payment_method_id": self.payconiq_payment_method.id,
                "pos_order_id": order.id,
            },
        )

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_valid_signature_returns_200(self):
        """Valid signature returns 200 """
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        response = self._call_webhook(payload)
        self.assertEqual(response.status_code, 200)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_missing_signature_returns_403(self):
        """Missing Signature header returns 403 """
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        response = self.url_open("/webhook/payconiq", data=json.dumps(payload), headers={
            "Content-Type": "application/json",
        })
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_invalid_signature_returns_403(self):
        """Invalid Signature header returns 403 """
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        response = self._call_webhook(payload, signature="qsdqsdq.qsdqsd.qsd")
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_tampered_payload_returns_403(self):
        """Tampered payload returns 403."""
        original_payload = {"paymentId": self.test_payconiq_id, "status": "FAILED"}
        tampered_payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}

        # Sign original payload
        signature = self._create_jws(json.dumps(original_payload).encode())

        # Send tampered payload with original signature
        response = self._call_webhook(tampered_payload, signature=signature)

        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_kid_not_found_returns_403(self):
        """Unknown kid returns 403."""
        # Return JWKS with different kid
        _other_private, other_public = self.utils.generate_ec_keypair()
        other_jwk = self.utils.create_jwk(other_public, "other-kid")

        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}

        response = self._call_webhook(payload, jwks=[other_jwk])

        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_wrong_key_returns_403(self):
        """Signature with wrong key returns 403."""
        # Create a different key pair for JWKS
        _other_private, other_public = self.utils.generate_ec_keypair()
        wrong_jwk = self.utils.create_jwk(other_public, self.kid)

        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}

        # Sign with our key but return different public key in JWKS
        response = self._call_webhook(payload, jwks=[wrong_jwk])
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_invalid_issuer_returns_403(self):
        """Invalid issuer returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header(**{const.ISS_KEY: "https://fake.com"})
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)

        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_expired_iat_returns_403(self):
        """Expired iat returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header(**{const.IAT_KEY: "2020-01-01T00:00:00.000Z"})
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)
        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_invalid_iat_format_returns_403(self):
        """Invalid iat format returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header(**{const.IAT_KEY: "not-a-date"})
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)

        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_missing_jti_returns_403(self):
        """Missing jti returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header()
        del header[const.JTI_KEY]
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)
        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_path_mismatch_returns_403(self):
        """Path mismatch returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header(**{const.PATH_KEY: "https://other.com/webhook"})
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)

        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_invalid_ppid_returns_403(self):
        """Invalid ppid returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header(**{const.SUB_KEY: "unknown-ppid"})
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)

        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    @mute_logger("odoo.addons.pos_payconiq.controllers.payconiq_controller")
    def test_missing_crits_returns_403(self):
        """Missing crit fields returns 403."""
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        header = self._create_header(crit=[const.ISS_KEY])
        signature = self.utils.sign_jws(self.private_key, header, payload_bytes)

        response = self._call_webhook(payload, signature=signature)
        self.assertTrue(self.payconiq_payment.payment_status, "waitingScan")
        self.assertEqual(response.status_code, 403)

    def test_uses_cached_jwk(self):
        """Uses cached JWK without fetching."""
        self._set_jwk_cache([self.jwk])

        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_jws(payload_bytes)

        with patch("odoo.addons.pos_payconiq.controllers.payconiq_controller.requests.get") as mock_get:
            mock_get.return_value = self.utils.create_jwks_response([self.jwk])

            response = self.url_open(
                "/webhook/payconiq",
                data=json.dumps(payload),
                headers={
                    "Content-Type": "application/json",
                    "Signature": signature,
                },
            )

            # Cache should be used, requests.get should not be called
            mock_get.assert_not_called()

        self.assertEqual(self.payconiq_payment.payment_status, "done")
        self.assertEqual(response.status_code, 200)

    def test_fetches_jwks_when_cache_expired(self):
        """Fetches fresh JWKS when cache is expired."""
        old_timestamp = (
                datetime.now(timezone.utc) - timedelta(hours=const.JWKS_TTL + 1)
        )
        self._set_jwk_cache([self.jwk], timestamp=old_timestamp.isoformat())

        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()

        new_private, new_public = self.utils.generate_ec_keypair()
        new_jwk = self.utils.create_jwk(new_public, self.kid)
        signature = self._create_jws(payload_bytes, private_key=new_private)

        with patch("odoo.addons.pos_payconiq.controllers.payconiq_controller.requests.get") as mock_get:
            mock_get.return_value = self.utils.create_jwks_response([new_jwk])

            response = self.url_open(
                "/webhook/payconiq",
                data=json.dumps(payload),
                headers={
                    "Content-Type": "application/json",
                    "Signature": signature,
                },
            )

            # Cache is expired, requests.get should be called
            mock_get.assert_called_once()

        # Verify cache was updated with new JWKS
        cache = self._get_jwk_cache()
        self.assertEqual(len(cache["jwks"]), 1)
        self.assertEqual(cache["jwks"][0]["kid"], self.kid)
        self.assertEqual(cache["jwks"][0]["x"], new_jwk["x"])
        self.assertEqual(cache["jwks"][0]["y"], new_jwk["y"])

        cache_timestamp = datetime.fromisoformat(cache["timestamp"])
        self.assertGreater(cache_timestamp, old_timestamp)
        self.assertEqual(self.payconiq_payment.payment_status, "done")
        self.assertEqual(response.status_code, 200)

    def test_fetches_jwks_when_kid_not_in_cache(self):
        """Fetches fresh JWKS when kid not found in cache."""
        # Cache with different kid
        _other_private, other_public = self.utils.generate_ec_keypair()
        other_jwk = self.utils.create_jwk(other_public, "other-kid")
        self._set_jwk_cache([other_jwk])

        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        payload_bytes = json.dumps(payload).encode()
        signature = self._create_jws(payload_bytes)

        with patch("odoo.addons.pos_payconiq.controllers.payconiq_controller.requests.get") as mock_get:
            # Return our JWK in the fresh fetch
            mock_get.return_value = self.utils.create_jwks_response([self.jwk])

            response = self.url_open(
                "/webhook/payconiq",
                data=json.dumps(payload),
                headers={
                    "Content-Type": "application/json",
                    "Signature": signature,
                },
            )

            # Kid not in cache, requests.get should be called
            mock_get.assert_called_once()
            self.assertEqual(self.payconiq_payment.payment_status, "done")
            self.assertEqual(response.status_code, 200)

        cache = self._get_jwk_cache()
        self.assertEqual(len(cache["jwks"]), 1)
        self.assertEqual(cache["jwks"][0]["kid"], self.kid)
        self.assertEqual(cache["jwks"][0]["x"], self.jwk["x"])
        self.assertEqual(cache["jwks"][0]["y"], self.jwk["y"])

    # ---------------------------------------------------
    # Utils
    # ---------------------------------------------------

    def _get_successful_payload(self):
        payload = {"paymentId": self.test_payconiq_id, "status": "SUCCEEDED"}
        return json.dumps(payload).encode()

    def _create_header(self, **overrides):
        """Create protected header with optional overrides."""
        return self.utils.create_protected_header(
            kid=self.kid,
            url=f"{self.base_url()}/webhook/payconiq",
            ppid=self.test_ppid,
            **overrides,
        )

    def _create_jws(self, payload: bytes, header=None, private_key=None):
        """Create signed JWS for payload."""
        header = header or self._create_header()
        return self.utils.sign_jws(private_key or self.private_key, header, payload)

    def _set_jwk_cache(self, jwks, timestamp=None):
        """Set JWK cache in config parameters."""
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        cache = {
            "timestamp": timestamp,
            "jwks": jwks,
        }
        self.env["ir.config_parameter"].sudo().set_str(
            "pos_payconiq.jwk_cache", json.dumps(cache),
        )

    def _get_jwk_cache(self):
        """Get JWK cache from config parameters."""
        cache_param = self.env["ir.config_parameter"].sudo().get_str("pos_payconiq.jwk_cache")
        if not cache_param:
            return None
        return json.loads(cache_param)

    def _call_webhook(self, payload: dict, signature: str | None = None, jwks: list | None = None):
        """Call webhook endpoint with payload and signature."""
        payload_bytes = json.dumps(payload).encode()
        signature = signature or self._create_jws(payload_bytes)
        jwks = jwks if jwks is not None else [self.jwk]

        def _mock_jwks_get(url, **kwargs):
            return self.utils.create_jwks_response(jwks)

        with patch(
                "odoo.addons.pos_payconiq.controllers.payconiq_controller.requests.get",
                _mock_jwks_get,
        ):
            return self.url_open(
                "/webhook/payconiq",
                data=json.dumps(payload),
                headers={
                    "Content-Type": "application/json",
                    "Signature": signature,
                },
            )


class PayconiqTestUtils:
    """Test utilities for Payconiq signature testing."""

    @staticmethod
    def b64url_encode(data: bytes) -> str:
        """Encode bytes to base64url without padding."""
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    @staticmethod
    def generate_ec_keypair():
        """Generate EC P-256 key pair."""
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        return private_key, private_key.public_key()

    @classmethod
    def create_jwk(cls, public_key, kid: str) -> dict:
        """Create JWK from EC public key."""
        public_numbers = public_key.public_numbers()
        return {
            "kty": "EC",
            "crv": "P-256",
            "x": cls.b64url_encode(public_numbers.x.to_bytes(32, "big")),
            "y": cls.b64url_encode(public_numbers.y.to_bytes(32, "big")),
            "kid": kid,
        }

    @classmethod
    def sign_jws(cls, private_key, protected_header: dict, payload: bytes) -> str:
        """Create detached JWS signature (protected..signature)."""
        protected_b64 = cls.b64url_encode(
            json.dumps(protected_header, separators=(",", ":")).encode(),
        )
        payload_b64 = cls.b64url_encode(payload)
        signing_input = f"{protected_b64}.{payload_b64}".encode()

        signature_der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(signature_der)
        signature_raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        signature_b64 = cls.b64url_encode(signature_raw)

        return f"{protected_b64}..{signature_b64}"

    @staticmethod
    def create_protected_header(
            kid: str,
            url: str,
            ppid: str,
            **overrides,
    ) -> dict:
        """Create valid protected header with optional overrides."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        header = {
            "alg": "ES256",
            "kid": kid,
            "crit": [
                const.ISS_KEY,
                const.IAT_KEY,
                const.JTI_KEY,
                const.PATH_KEY,
                const.SUB_KEY,
            ],
            const.ISS_KEY: const.ISS_VALUE,
            const.IAT_KEY: now,
            const.JTI_KEY: "unique-jti-12345",
            const.PATH_KEY: url,
            const.SUB_KEY: ppid,
        }
        header.update(overrides)
        return header

    @staticmethod
    def create_jwks_response(jwks: list) -> Response:
        """Create a mock Response object for JWKS endpoint."""
        response = Response()
        response.status_code = 200
        response._content = json.dumps({"keys": jwks}).encode()
        return response
