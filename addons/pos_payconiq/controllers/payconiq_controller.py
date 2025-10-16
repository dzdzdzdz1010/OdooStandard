import base64
import json
import logging
from binascii import Error as BinasciiError
from datetime import datetime, timedelta, timezone

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

from odoo import http
from odoo.http import request

from odoo.addons.pos_payconiq import const

_logger = logging.getLogger(__name__)


class PayconiqController(http.Controller):

    @http.route(["/webhook/payconiq"], type="http", auth="public", methods=["POST"], csrf=False)
    def payconiq_webhook(self, mode=None):
        """
        Handle the Payconiq webhook callback.

        This endpoint is triggered by Payconiq to notify about payment updates.
        It verifies the request signature, processes the payment data, and sends
        a synchronization message to the POS system.
        """

        try:
            signature_payconiq_ppid = self._verify_payconiq_signature(request.httprequest, mode == "test")
        except PayconiqSignatureValidationError as e:
            _logger.warning("Payconiq signature verification failed: %s", e)
            return http.Response(status=403)

        data = request.get_json_data()
        payconiq_payment_id = data.get("paymentId")

        pos_payment = None
        if payconiq_payment_id:
            pos_payment = self.env["pos.payment"].sudo().search([("payconiq_id", "=", payconiq_payment_id)], limit=1)

        if not pos_payment or not pos_payment.exists():
            return http.Response("Payment not found.", status=404)

        if mode != "test" and signature_payconiq_ppid != pos_payment.payment_method_id.payconiq_ppid:
            _logger.warning("Payconiq profile ID mismatch")
            return http.Response(status=403)

        payconiq_status = data.get("status")

        def _notify_pos():
            pos_order = pos_payment.pos_order_id
            pos_order.config_id._notify(
                "PAYCONIQ_PAYMENTS_NOTIFICATION",
                {
                    "order_id": pos_order.id,
                    "payment_id": pos_payment.id,
                    "payconiq_status": payconiq_status,
                },
            )

        if pos_payment.payment_status != "done":
            if payconiq_status == "SUCCEEDED":
                pos_payment.payment_status = "done"
                pos_payment.qr_code = False
                _notify_pos()
            elif payconiq_status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED") and pos_payment.payment_status != "retry":
                pos_payment.payment_status = "retry"
                pos_payment.qr_code = False
                pos_payment.payconiq_id = False
                _notify_pos()

            # PENDING, IDENTIFIED, AUTHORIZED, PENDING_MERCHANT_ACKNOWLEDGEMENT, VOIDED --> no action
            # https://docs.payconiq.be/guides/general/callback052025

        return http.Response(status=200)

    # ========================================== #

    def _verify_payconiq_signature(self, request, test_mode):
        """
        Main entry point to verify the signature of a Payconiq callback request.

        Steps:
            1. Bypass signature check in test mode.
            2. Extract the protected header, signature, and key ID from the JWS.
            3. Retrieve the JWK (JSON Web Key) based on the key ID.
            4. Construct the public key object (EC or RSA) from the JWK.
            5. Verify the detached JWS signature using the request body.
            6. Validate all critical JOSE header fields required by Payconiq.

        Raises:
            PayconiqSignatureValidationError: If the signature is invalid or critical header check fails.
        """

        protected_b64, signature_b64, kid, protected = self._extract_jws_parts(request)
        jwk = self._get_jwk_by_kid(kid, test_mode)
        public_key = self._build_public_key(jwk)
        self._verify_signature(
            public_key=public_key,
            protected_b64=protected_b64,
            body=request.data,
            signature_b64=signature_b64,
        )
        return self._validate_critical_headers(protected, request.url)

    # ========================================== #

    def _verify_signature(self, public_key, protected_b64, body, signature_b64):
        """
        Verify the detached JWS signature using the reconstructed public key.
        Supports both ES256 (ECDSA) and RS256 (RSA) signatures.

        :param public_key: The EC public key object from the JWK.
        :param protected_b64: The base64url-encoded protected header string.
        :param body: The raw HTTP request body (as bytes).
        :param signature_b64: The base64url-encoded signature string.
        :raises PayconiqSignatureValidationError: If the signature verification fails.
        """

        # Rebuild the signed input: base64url(protected header) + "." + base64url(payload)
        payload_b64 = base64.urlsafe_b64encode(body).decode().rstrip("=")
        signed_data = f"{protected_b64}.{payload_b64}".encode()

        # Decode the signature from base64url
        signature_bytes = self._b64url_decode(signature_b64)

        # Handle EC (ES256)
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            if len(signature_bytes) == 64:  # raw (r,s)
                r = int.from_bytes(signature_bytes[:32], "big")
                s = int.from_bytes(signature_bytes[32:], "big")
                signature_bytes = encode_dss_signature(r, s)

            try:
                public_key.verify(signature_bytes, signed_data, ec.ECDSA(SHA256()))
            except InvalidSignature as e:
                raise PayconiqSignatureValidationError("ECDSA signature verification failed.") from e

        # Handle RSA (RS256)
        elif isinstance(public_key, rsa.RSAPublicKey):
            try:
                public_key.verify(
                    signature_bytes,
                    signed_data,
                    padding.PKCS1v15(),
                    SHA256(),
                )
            except InvalidSignature as e:
                raise PayconiqSignatureValidationError("RSA signature verification failed.") from e
        # Unsupported key type
        else:
            raise PayconiqSignatureValidationError("Unsupported public key type")

    def _validate_critical_headers(self, protected: dict, request_url: str):
        """Validate Payconiq-specific critical headers in the JWS protected header."""
        crit_errors = []

        # Validate all crits are included
        crits = protected.get("crit", [])
        expected_crits = [
            const.ISS_KEY,
            const.IAT_KEY,
            const.JTI_KEY,
            const.PATH_KEY,
            const.SUB_KEY,
        ]
        missing_crits = [key for key in expected_crits if key not in crits]
        if missing_crits:
            crit_errors.append(f"Missing crits: {missing_crits}")

        # Validate issuer (iss)
        issuer = protected.get(const.ISS_KEY)
        if issuer != const.ISS_VALUE:
            crit_errors.append(f"Invalid issuer: {issuer}")

        # Validate issued-at time (iat) is recent
        iat_str = protected.get(const.IAT_KEY)
        try:
            issued_at = datetime.strptime(iat_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            issued_at = issued_at.replace(tzinfo=timezone.utc)
            delta = (datetime.now(timezone.utc) - issued_at).total_seconds()
            if delta > 5:  # 5 seconds tolerance
                crit_errors.append(f"Issued-at time too old: {iat_str}")
        except (TypeError, ValueError) as e:
            crit_errors.append(f"Invalid or missing iat format: {e}")

        # Validate jti (unique ID)
        jti = protected.get(const.JTI_KEY)
        if not jti:
            crit_errors.append("Missing jti")

        # Validate path
        expected_path = request_url.replace("http://", "https://")
        jws_path = protected.get(const.PATH_KEY).replace("http://", "https://")
        if jws_path != expected_path:
            crit_errors.append(f"Path mismatch: {jws_path} != {expected_path}")

        # Validate subject matches the configured payment profile ID
        payconiq_profile_id = protected.get(const.SUB_KEY)

        if crit_errors:
            raise PayconiqSignatureValidationError(crit_errors)

        return payconiq_profile_id

    def _extract_jws_parts(self, request):
        """
        Extract the parts of a detached JWS signature from the HTTP request header.

        Returns:
            protected_b64: base64url-encoded protected header
            signature_b64: base64url-encoded signature
            kid: key ID used to retrieve the JWK
            protected: decoded JOSE header as dict
        """
        # Get the 'Signature' header
        signature = request.headers.get("Signature")
        if not signature:
            raise PayconiqSignatureValidationError("Missing Signature header")

        # The JWS is in the form: protected_b64..signature_b64 (note: payload is detached)
        try:
            protected_b64, _empty_playload_64, signature_b64 = signature.split(".")
        except (ValueError, AttributeError, TypeError) as e:
            raise PayconiqSignatureValidationError("Malformed Signature format.") from e

        # Decode the protected header (JOSE header)
        try:
            protected_json = self._b64url_decode(protected_b64).decode("utf-8")
            protected = json.loads(protected_json)
            kid = protected["kid"]  # Get the Key ID used to fetch the JWK
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as e:
            raise PayconiqSignatureValidationError("Unable to decode or parse protected header.") from e

        return protected_b64, signature_b64, kid, protected

    def _get_jwk_by_kid(self, kid: str, test_mode: bool):
        """Retrieve the JWK (JSON Web Key) by its Key ID (kid), retrying JWKS fetch if needed."""
        now = datetime.now(timezone.utc)
        cache_param = (
            request.env["ir.config_parameter"].sudo().get_str("pos_payconiq.jwk_cache")
        )
        cache = json.loads(cache_param) if cache_param else {}
        cache_jwks = cache.get("jwks", [])
        cache_timestamp = cache.get("timestamp", None)
        if cache_timestamp:
            cache_timestamp = datetime.fromisoformat(cache_timestamp)

        # Use cached JWKS if valid
        if (
            cache_jwks
            and cache_timestamp
            and (now - cache_timestamp) < timedelta(hours=const.JWKS_TTL)
        ):
            jwks = cache_jwks
        else:
            jwks = []

        # Extract the JWK with the matching kid
        jwks_by_kid = {key["kid"]: key for key in jwks if "kid" in key}
        jwk_data = jwks_by_kid.get(kid)
        if jwk_data:
            return jwk_data

        # Fetch fresh JWKS from Payconiq if not found in cache
        jwks_url = const.API_URLS["preprod" if test_mode else "production"]["jwks"]
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        jwks = response.json().get("keys", [])

        jwk_data = jwks_by_kid.get(kid)
        if not jwk_data:
            raise PayconiqSignatureValidationError(f"JWK with kid {kid} not found after JWKS refresh")

        request.env["ir.config_parameter"].sudo().set_str(
            "pos_payconiq.jwk_cache",
            json.dumps(
                {
                    "timestamp": now.isoformat(),
                    "jwks": jwks,
                },
            ),
        )
        return jwk_data

    def _build_public_key(self, jwk: dict):
        """Build a public key object from the JWK data."""
        kty = jwk.get("kty")

        if kty == "EC":
            x_bytes = self._b64url_decode(jwk["x"])
            y_bytes = self._b64url_decode(jwk["y"])
            public_numbers = ec.EllipticCurvePublicNumbers(
                int.from_bytes(x_bytes, byteorder="big"),
                int.from_bytes(y_bytes, byteorder="big"),
                ec.SECP256R1(),
            )
            return public_numbers.public_key(default_backend())

        if kty == "RSA":
            n = int.from_bytes(self._b64url_decode(jwk["n"]), byteorder="big")
            e = int.from_bytes(self._b64url_decode(jwk["e"]), byteorder="big")
            public_numbers = rsa.RSAPublicNumbers(e, n)
            return public_numbers.public_key(default_backend())

        raise PayconiqSignatureValidationError(f"Unsupported key type: {kty}")

    def _b64url_decode(self, data: str) -> bytes:
        """Decode a base64url-encoded string without padding."""
        try:
            missing_padding = len(data) % 4
            if missing_padding:
                data += "=" * (4 - missing_padding)
            return base64.urlsafe_b64decode(data)
        except (ValueError, TypeError, BinasciiError) as e:
            raise PayconiqSignatureValidationError("Base64url decode error") from e


class PayconiqSignatureValidationError(Exception):
    pass
