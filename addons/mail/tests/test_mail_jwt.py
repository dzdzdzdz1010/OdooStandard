# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import json

from freezegun import freeze_time

from odoo.tests.common import BaseCase, tagged

from odoo.addons.mail.tools import jwt


@tagged("mail_jwt")
class TestMailJwt(BaseCase):
    def test_hs256_sign_verify(self):
        sub_val = "1234567890"
        name_val = "spam"
        secret = base64.urlsafe_b64encode(b"my_secret_key").decode("ascii")
        claims = {"sub": sub_val, "name": name_val, "iat": 1516239022}

        token = jwt.sign(claims, secret, ttl=60, algorithm=jwt.Algorithm.HS256)

        self.assertIsInstance(token, str)
        parts = token.split(".")
        self.assertEqual(len(parts), 3)

        decoded = jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)
        self.assertEqual(decoded["sub"], sub_val)
        self.assertEqual(decoded["name"], name_val)

    def test_es256_sign_verify(self):
        sub_val = "eggs"
        private_key, public_key = jwt.generate_vapid_keys()
        claims = {"sub": sub_val, "admin": True}

        token = jwt.sign(claims, private_key, ttl=300, algorithm=jwt.Algorithm.ES256)
        decoded = jwt.verify(token, public_key, algorithm=jwt.Algorithm.ES256)
        self.assertEqual(decoded["sub"], sub_val)
        self.assertTrue(decoded["admin"])

    def test_token_expiration(self):
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        claims = {"foo": "bar"}

        with freeze_time("2023-01-01 12:00:00"):
            token = jwt.sign(claims, secret, ttl=60, algorithm=jwt.Algorithm.HS256)

        # 30 seconds later
        with freeze_time("2023-01-01 12:00:30"):
            jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)

        # 61 seconds later
        with freeze_time("2023-01-01 12:01:01"):
            with self.assertRaisesRegex(ValueError, "Token expired"):
                jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)

    def test_invalid_signature(self):
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        claims = {"foo": "bar"}
        token = jwt.sign(claims, secret, ttl=60, algorithm=jwt.Algorithm.HS256)

        header, _, sig = token.split(".")
        fake_payload = (
            base64.urlsafe_b64encode(json.dumps({"foo": "baz"}).encode())
            .decode()
            .strip("=")
        )
        bad_token = f"{header}.{fake_payload}.{sig}"

        with self.assertRaisesRegex(ValueError, "Invalid signature"):
            jwt.verify(bad_token, secret, algorithm=jwt.Algorithm.HS256)

    def test_wrong_key(self):
        secret1 = base64.urlsafe_b64encode(b"secret1").decode("ascii")
        secret2 = base64.urlsafe_b64encode(b"secret2").decode("ascii")
        token = jwt.sign({}, secret1, ttl=60, algorithm=jwt.Algorithm.HS256)

        with self.assertRaisesRegex(ValueError, "Invalid signature"):
            jwt.verify(token, secret2, algorithm=jwt.Algorithm.HS256)

    def test_malformed_token(self):
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        with self.assertRaisesRegex(ValueError, "Invalid token format"):
            jwt.verify("he.he", secret, algorithm=jwt.Algorithm.HS256)

    def test_invalid_algorithm_header(self):
        header = (
            base64.urlsafe_b64encode(json.dumps({"typ": "JWT", "alg": "none"}).encode())
            .decode()
            .strip("=")
        )
        payload = base64.urlsafe_b64encode(json.dumps({}).encode()).decode().strip("=")
        token = f"{header}.{payload}."

        secret = base64.urlsafe_b64encode(b"s").decode("ascii")

        with self.assertRaisesRegex(ValueError, "Invalid algorithm"):
            jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)

    def test_mismatched_algorithm_usage(self):
        secret = base64.urlsafe_b64encode(b"s").decode("ascii")
        token = jwt.sign({}, secret, ttl=60, algorithm=jwt.Algorithm.HS256)
        _, public_key = jwt.generate_vapid_keys()

        with self.assertRaisesRegex(ValueError, "Invalid algorithm"):
            jwt.verify(token, public_key, algorithm=jwt.Algorithm.ES256)

    # -------------------------------------------------------------------------
    # ES256 Algorithm Edge Cases
    # -------------------------------------------------------------------------

    def test_es256_invalid_signature(self):
        """Test ES256 verification fails with tampered payload."""
        private_key, public_key = jwt.generate_vapid_keys()
        claims = {"sub": "user123"}
        token = jwt.sign(claims, private_key, ttl=60, algorithm=jwt.Algorithm.ES256)

        header, _, sig = token.split(".")
        fake_payload = (
            base64.urlsafe_b64encode(json.dumps({"sub": "attacker"}).encode())
            .decode()
            .strip("=")
        )
        bad_token = f"{header}.{fake_payload}.{sig}"

        with self.assertRaisesRegex(ValueError, "Invalid signature"):
            jwt.verify(bad_token, public_key, algorithm=jwt.Algorithm.ES256)

    def test_es256_wrong_key(self):
        """Test ES256 verification fails with different key pair."""
        private_key1, _ = jwt.generate_vapid_keys()
        _, public_key2 = jwt.generate_vapid_keys()

        token = jwt.sign({"data": "secret"}, private_key1, ttl=60, algorithm=jwt.Algorithm.ES256)

        with self.assertRaisesRegex(ValueError, "Invalid signature"):
            jwt.verify(token, public_key2, algorithm=jwt.Algorithm.ES256)

    def test_es256_invalid_signature_length(self):
        """Test ES256 verification fails with incorrect signature length."""
        private_key, public_key = jwt.generate_vapid_keys()
        token = jwt.sign({}, private_key, ttl=60, algorithm=jwt.Algorithm.ES256)

        header, payload, _ = token.split(".")
        # Create a signature that's not 64 bytes
        bad_sig = base64.urlsafe_b64encode(b"short").decode().strip("=")
        bad_token = f"{header}.{payload}.{bad_sig}"

        with self.assertRaisesRegex(ValueError, "Invalid signature length"):
            jwt.verify(bad_token, public_key, algorithm=jwt.Algorithm.ES256)

    # -------------------------------------------------------------------------
    # Token Structure Validation
    # -------------------------------------------------------------------------

    def test_invalid_base64_header(self):
        """Test verification fails with malformed base64 in header."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        # Can raise binascii.Error, UnicodeDecodeError, or json.JSONDecodeError
        with self.assertRaises(Exception):
            jwt.verify("@@@.payload.sig", secret, algorithm=jwt.Algorithm.HS256)

    def test_invalid_base64_payload(self):
        """Test verification fails with malformed base64 in payload."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        header = (
            base64.urlsafe_b64encode(json.dumps({"typ": "JWT", "alg": "HS256"}).encode())
            .decode()
            .strip("=")
        )
        # Can raise binascii.Error, UnicodeDecodeError, or json.JSONDecodeError
        with self.assertRaises(Exception):
            jwt.verify(f"{header}.@@@.sig", secret, algorithm=jwt.Algorithm.HS256)

    def test_invalid_json_header(self):
        """Test verification fails with valid base64 but invalid JSON in header."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        bad_header = base64.urlsafe_b64encode(b"not json").decode().strip("=")
        payload = base64.urlsafe_b64encode(json.dumps({}).encode()).decode().strip("=")

        with self.assertRaises(json.JSONDecodeError):
            jwt.verify(f"{bad_header}.{payload}.sig", secret, algorithm=jwt.Algorithm.HS256)

    def test_invalid_json_payload(self):
        """Test verification fails with valid base64 but invalid JSON in payload."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        header = (
            base64.urlsafe_b64encode(json.dumps({"typ": "JWT", "alg": "HS256"}).encode())
            .decode()
            .strip("=")
        )
        bad_payload = base64.urlsafe_b64encode(b"not json").decode().strip("=")

        with self.assertRaises(json.JSONDecodeError):
            jwt.verify(f"{header}.{bad_payload}.sig", secret, algorithm=jwt.Algorithm.HS256)

    def test_empty_token_parts(self):
        """Test verification fails with empty token parts."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        with self.assertRaises(Exception):
            jwt.verify("..", secret, algorithm=jwt.Algorithm.HS256)

    # -------------------------------------------------------------------------
    # Claims Handling
    # -------------------------------------------------------------------------

    def test_claims_preserved(self):
        """Test all custom claims survive round-trip signing/verification."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        claims = {
            "sub": "user123",
            "name": "Test User",
            "admin": True,
            "level": 42,
            "ratio": 3.14,
            "tags": ["a", "b", "c"],
            "metadata": {"nested": {"deep": "value"}},
        }

        token = jwt.sign(claims.copy(), secret, ttl=60, algorithm=jwt.Algorithm.HS256)
        decoded = jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)

        for key, value in claims.items():
            self.assertEqual(decoded[key], value, f"Claim '{key}' not preserved")

    def test_special_characters_in_claims(self):
        """Test claims with unicode and special characters."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        claims = {
            "unicode": "日本語 中文 한국어 émøjįs 🎉🚀",
            "special": "quotes: \"'` and slashes: /\\ and newlines:\n\t",
            "html": "<script>alert('xss')</script>",
        }

        token = jwt.sign(claims.copy(), secret, ttl=60, algorithm=jwt.Algorithm.HS256)
        decoded = jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)

        for key, value in claims.items():
            self.assertEqual(decoded[key], value)

    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------

    def test_sign_with_zero_ttl(self):
        """Test that signing with ttl=0 raises an assertion error."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        with self.assertRaises(AssertionError):
            jwt.sign({}, secret, ttl=0, algorithm=jwt.Algorithm.HS256)

    def test_sign_with_negative_ttl(self):
        """Test behavior with negative TTL - token should be immediately expired."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        # Negative TTL passes the assert (it's truthy) but creates an expired token
        token = jwt.sign({}, secret, ttl=-60, algorithm=jwt.Algorithm.HS256)

        with self.assertRaisesRegex(ValueError, "Token expired"):
            jwt.verify(token, secret, algorithm=jwt.Algorithm.HS256)

    def test_unsupported_algorithm_in_verify(self):
        """Test that unsupported algorithm in verify raises ValueError."""
        secret = base64.urlsafe_b64encode(b"secret").decode("ascii")
        token = jwt.sign({}, secret, ttl=60, algorithm=jwt.Algorithm.HS256)

        # Modify the header to have an unsupported algorithm that matches what we pass
        _, payload, sig = token.split(".")
        # We can't easily test the default branch since Algorithm is an enum
        # But we can test algorithm mismatch which triggers different error
        bad_header = base64.urlsafe_b64encode(
            json.dumps({"typ": "JWT", "alg": "RS256"}).encode(),
        ).decode().strip("=")
        bad_token = f"{bad_header}.{payload}.{sig}"

        with self.assertRaisesRegex(ValueError, "Invalid algorithm"):
            jwt.verify(bad_token, secret, algorithm=jwt.Algorithm.HS256)

    # -------------------------------------------------------------------------
    # Key Format Handling
    # -------------------------------------------------------------------------

    def test_key_with_padding(self):
        """Test that keys with base64 padding work correctly."""
        raw_secret = b"secret_key_123"  # Length not multiple of 3
        secret_with_padding = base64.urlsafe_b64encode(raw_secret).decode("ascii")
        self.assertIn("=", secret_with_padding)

        claims = {"test": "data"}
        token = jwt.sign(claims, secret_with_padding, ttl=60, algorithm=jwt.Algorithm.HS256)
        decoded = jwt.verify(token, secret_with_padding, algorithm=jwt.Algorithm.HS256)
        self.assertEqual(decoded["test"], "data")

    def test_key_without_padding(self):
        """Test that keys without base64 padding work correctly."""
        # Create a key without padding (length multiple of 3 bytes = 4 base64 chars)
        raw_secret = b"secretkey123"  # 12 bytes = 16 base64 chars, no padding
        secret_no_padding = base64.urlsafe_b64encode(raw_secret).decode("ascii")
        self.assertNotIn("=", secret_no_padding)  # Verify no padding

        claims = {"test": "data"}
        token = jwt.sign(claims, secret_no_padding, ttl=60, algorithm=jwt.Algorithm.HS256)
        decoded = jwt.verify(token, secret_no_padding, algorithm=jwt.Algorithm.HS256)
        self.assertEqual(decoded["test"], "data")

    # -------------------------------------------------------------------------
    # VAPID Key Generation
    # -------------------------------------------------------------------------

    def test_vapid_keys_generation(self):
        private_key, public_key = jwt.generate_vapid_keys()
        self.assertIsInstance(private_key, str)
        self.assertIsInstance(public_key, str)

        try:
            jwt.base64_decode_with_padding(private_key)
            jwt.base64_decode_with_padding(public_key)
        except binascii.Error:
            self.fail("Keys are not valid base64 strings")

    def test_vapid_keys_uniqueness(self):
        """Test that multiple calls generate different key pairs."""
        keys = [jwt.generate_vapid_keys() for _ in range(5)]
        private_keys = [k[0] for k in keys]
        public_keys = [k[1] for k in keys]

        # All private keys should be unique
        self.assertEqual(len(set(private_keys)), 5)
        # All public keys should be unique
        self.assertEqual(len(set(public_keys)), 5)

    def test_vapid_key_lengths(self):
        """Test VAPID keys have correct byte lengths."""
        private_key, public_key = jwt.generate_vapid_keys()

        private_bytes = jwt.base64_decode_with_padding(private_key)
        public_bytes = jwt.base64_decode_with_padding(public_key)

        # Private key should be 32 bytes (256 bits for P-256 curve)
        self.assertEqual(len(private_bytes), 32)
        # Public key should be 65 bytes (uncompressed point: 0x04 + 32 bytes x + 32 bytes y)
        self.assertEqual(len(public_bytes), 65)
        # Uncompressed point format starts with 0x04
        self.assertEqual(public_bytes[0], 0x04)
