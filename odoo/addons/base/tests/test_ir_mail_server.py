# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import email.message
import email.policy
import contextlib
import logging
import shutil
import smtplib
import socket
import ssl
import unittest
import warnings

from base64 import b64encode
from os import getenv
from pathlib import Path
from socket import getaddrinfo  # keep a reference on the non-patched function
from unittest.mock import patch

import psycopg2.errors

from odoo.addons.base.models.ir_mail_server import IrMail_Server
from odoo.addons.base.tests import mail_examples
from odoo.addons.base.tests.common import MockSmtplibCase, TransactionCaseWithUserDemo
from odoo.exceptions import UserError
from odoo.tests import tagged, users
from odoo.tests.common import TransactionCase
from odoo.tools import config, file_path, mute_logger

try:
    import aiosmtpd
    import aiosmtpd.controller
    import aiosmtpd.smtp
    import aiosmtpd.handlers
except ImportError:
    aiosmtpd = None


SMTP_TIMEOUT = 5
PASSWORD = 'secretpassword'
_openssl = shutil.which('openssl')
_logger = logging.getLogger(__name__)


class _FakeSMTP:
    """SMTP stub"""
    def __init__(self):
        self.messages = []
        self.from_filter = 'example.com'

    # Python 3 before 3.7.4
    def sendmail(self, smtp_from, smtp_to_list, message_str,
                 mail_options=(), rcpt_options=()):
        self.messages.append(message_str)

    # Python 3.7.4+
    def send_message(self, message, smtp_from, smtp_to_list,
                     mail_options=(), rcpt_options=()):
        self.messages.append(message.as_string())


@tagged('mail_server')
@tagged('at_install', '-post_install')  # LEGACY at_install
class EmailConfigCase(TransactionCase):

    @patch.dict(config.options, {"email_from": "settings@example.com"})
    def test_default_email_from(self):
        """ Email from setting is respected and comes from configuration. """
        message = self.env["ir.mail_server"]._build_email__(
            False, "recipient@example.com", "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "settings@example.com")


@tagged('mail_server')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestIrMailServer(TransactionCase, MockSmtplibCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_str('mail.default.from_filter', None)
        cls._init_mail_servers()

    def test_assert_base_values(self):
        self.assertFalse(self.env['ir.mail_server']._get_default_bounce_address())
        self.assertFalse(self.env['ir.mail_server']._get_default_from_address())

    def test_bpo_34424_35805(self):
        """Ensure all email sent are bpo-34424 and bpo-35805 free"""
        fake_smtp = _FakeSMTP()
        msg = email.message.EmailMessage(policy=email.policy.SMTP)
        msg['From'] = '"Joé Doe" <joe@example.com>'
        msg['To'] = '"Joé Doe" <joe@example.com>'

        # Message-Id & References fields longer than 77 chars (bpo-35805)
        msg['Message-Id'] = '<929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>'
        msg['References'] = '<345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>'

        msg_on_the_wire = self._send_email(msg, fake_smtp)
        self.assertEqual(msg_on_the_wire,
            'From: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n'
            'To: =?utf-8?q?Jo=C3=A9?= Doe <joe@example.com>\r\n'
            'Message-Id: <929227342217024.1596730490.324691772460938-example-30661-some.reference@test-123.example.com>\r\n'
            'References: <345227342212345.1596730777.324691772483620-example-30453-other.reference@test-123.example.com>\r\n'
            '\r\n'
        )

    def test_content_alternative_correct_order(self):
        """
        RFC-1521 7.2.3. The Multipart/alternative subtype
        > the alternatives appear in an order of increasing faithfulness
        > to the original content. In general, the best choice is the
        > LAST part of a type supported by the recipient system's local
        > environment.

        Also, the MIME-Version header should be present in BOTH the
        enveloppe AND the parts
        """
        fake_smtp = _FakeSMTP()
        msg = self._build_email("test@example.com", body='<p>Hello world</p>', subtype='html')
        msg_on_the_wire = self._send_email(msg, fake_smtp)

        self.assertGreater(msg_on_the_wire.index('text/html'), msg_on_the_wire.index('text/plain'),
            "The html part should be preferred (=appear after) to the text part")
        self.assertEqual(msg_on_the_wire.count('==============='), 2 + 2, # +2 for the header and the footer
            "There should be 2 parts: one text and one html")
        self.assertEqual(msg_on_the_wire.count('MIME-Version: 1.0'), 3,
            "There should be 3 headers MIME-Version: one on the enveloppe, "
            "one on the html part, one on the text part")

    def test_content_mail_body(self):
        bodies = [
            'content',
            '<p>content</p>',
            '<head><meta content="text/html; charset=utf-8" http-equiv="Content-Type"></head><body><p>content</p></body>',
            mail_examples.MISC_HTML_SOURCE,
            mail_examples.QUOTE_THUNDERBIRD_HTML,
        ]
        expected_list = [
            'content',
            'content',
            'content',
            "test1\n*test2*\ntest3\ntest4\ntest5\ntest6   test7\ntest8    test9\ntest10\ntest11\ntest12\ngoogle [1]\ntest link [2]\n\n\n[1] http://google.com\n[2] javascript:alert('malicious code')",
            'On 01/05/2016 10:24 AM, Raoul\nPoilvache wrote:\n\n* Test reply. The suite. *\n\n--\nRaoul Poilvache\n\nTop cool !!!\n\n--\nRaoul Poilvache',
        ]
        for body, expected in zip(bodies, expected_list):
            message = self.env['ir.mail_server']._build_email__(
                'john.doe@from.example.com',
                'destinataire@to.example.com',
                body=body,
                subject='Subject',
                subtype='html',
            )
            body_alternative = None
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                if part.get_content_type() == 'text/plain':
                    if not part.get_payload():
                        continue
                    # remove ending new lines as it just adds noise
                    body_alternative = part.get_content().rstrip('\n')
            self.assertEqual(body_alternative, expected)

    @mute_logger('odoo.sql_db')
    def test_mail_server_auth_cert_requires_tls(self):
        with self.assertRaises(psycopg2.errors.CheckViolation):
            self.env['ir.mail_server'].create({
                'name': 'test',
                'smtp_host': 'smtp_host',
                'smtp_encryption': 'none',
                'smtp_authentication': 'certificate',
            })

    @users('admin')
    def test_mail_server_get_test_email_from(self):
        """ Test the email used to test the mail server connection. Check
        from_filter parsing / default fallback value. """
        self.env.user.email = 'mitchell.admin@example.com'
        test_server = self.env['ir.mail_server'].create({
            'from_filter': 'example_2.com, example_3.com',
            'name': 'Test Server',
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
        })
        for from_filter, expected_test_email in zip(
            [
                'example_2.com, example_3.com',
                'dummy.com, full_email@example_2.com, dummy2.com',
                # fallback on user's email
                ' ',
                ',',
                False,
            ], [
                'noreply@example_2.com',
                'full_email@example_2.com',
                self.env.user.email,
                self.env.user.email,
                self.env.user.email,
            ],
        ):
            with self.subTest(from_filter=from_filter):
                test_server.from_filter = from_filter
                email_from = test_server._get_test_email_from()
                self.assertEqual(email_from, expected_test_email)

    def test_mail_server_match_from_filter(self):
        """ Test the from_filter field on the "ir.mail_server". """
        # Should match
        tests = [
            ('admin@mail.example.com', 'mail.example.com'),
            ('admin@mail.example.com', 'mail.EXAMPLE.com'),
            ('admin@mail.example.com', 'admin@mail.example.com'),
            ('admin@mail.example.com', False),
            ('"fake@test.mycompany.com" <admin@mail.example.com>', 'mail.example.com'),
            ('"fake@test.mycompany.com" <ADMIN@mail.example.com>', 'mail.example.com'),
            ('"fake@test.mycompany.com" <ADMIN@mail.example.com>', 'test.mycompany.com, mail.example.com, test2.com'),
        ]
        for email, from_filter in tests:
            self.assertTrue(self.env['ir.mail_server']._match_from_filter(email, from_filter))

        # Should not match
        tests = [
            ('admin@mail.example.com', 'test@mail.example.com'),
            ('admin@mail.example.com', 'test.mycompany.com'),
            ('admin@mail.example.com', 'mail.éxample.com'),
            ('admin@mmail.example.com', 'mail.example.com'),
            ('admin@mail.example.com', 'mmail.example.com'),
            ('"admin@mail.example.com" <fake@test.mycompany.com>', 'mail.example.com'),
            ('"fake@test.mycompany.com" <ADMIN@mail.example.com>', 'test.mycompany.com, wrong.mail.example.com, test3.com'),
        ]
        for email, from_filter in tests:
            self.assertFalse(self.env['ir.mail_server']._match_from_filter(email, from_filter))

    @mute_logger('odoo.models.unlink')
    def test_mail_server_priorities(self):
        """ Test if we choose the right mail server to send an email. Simulates
        simple Odoo DB so we have to spoof the FROM otherwise we cannot send
        any email. """
        for email_from, (expected_mail_server, expected_email_from) in zip(
            [
                'specific_user@test.mycompany.com',
                'unknown_email@test.mycompany.com',
                # no notification set, must be forced to spoof the FROM
                '"Test" <test@unknown_domain.com>',
            ], [
                (self.mail_server_user, 'specific_user@test.mycompany.com'),
                (self.mail_server_domain, 'unknown_email@test.mycompany.com'),
                (self.mail_server_default, '"Test" <test@unknown_domain.com>'),
            ],
        ):
            with self.subTest(email_from=email_from):
                mail_server, mail_from = self.env['ir.mail_server']._find_mail_server(email_from=email_from)
                self.assertEqual(mail_server, expected_mail_server)
                self.assertEqual(mail_from, expected_email_from)

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email(self):
        """ Test main 'send_email' usage: check mail_server choice based on from
        filters, encapsulation, spoofing. """
        IrMailServer = self.env['ir.mail_server']

        for mail_from, (expected_smtp_from, expected_msg_from, expected_mail_server) in zip(
            [
                'specific_user@test.mycompany.com',
                '"Name" <test@unknown_domain.com>',
                'test@unknown_domain.com',
                '"Name" <unknown_name@test.mycompany.com>'
            ], [
                # A mail server is configured for the email
                ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com', self.mail_server_user),
                # No mail server are configured for the email address, so it will use the
                # notifications email instead and encapsulate the old email
                ('test@unknown_domain.com', '"Name" <test@unknown_domain.com>', self.mail_server_default),
                # same situation, but the original email has no name part
                ('test@unknown_domain.com', 'test@unknown_domain.com', self.mail_server_default),
                # A mail server is configured for the entire domain name, so we can use the bounce
                # email address because the mail server supports it
                ('unknown_name@test.mycompany.com', '"Name" <unknown_name@test.mycompany.com>', self.mail_server_domain),
            ]
        ):
            # test with and without providing an SMTP session, which should not impact test
            for provide_smtp in [False, True]:
                with self.subTest(mail_from=mail_from, provide_smtp=provide_smtp):
                    with self.mock_smtplib_connection():
                        if provide_smtp:
                            smtp_session = IrMailServer._connect__(smtp_from=mail_from)
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message, smtp_session=smtp_session)
                        else:
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message)

                    self.connect_mocked.assert_called_once()
                    self.assertEqual(len(self.emails), 1)
                    self.assertSMTPEmailsSent(
                        smtp_from=expected_smtp_from,
                        message_from=expected_msg_from,
                        mail_server=expected_mail_server,
                    )

        # remove the notification server
        # so <notifications.test@test.mycompany.com> will use the <test.mycompany.com> mail server
        # The mail server configured for the notifications email has been removed
        # but we can still use the mail server configured for test.mycompany.com
        # and so we will be able to use the bounce address
        # because we use the mail server for "test.mycompany.com"
        self.mail_server_notification.unlink()
        for provide_smtp in [False, True]:
            with self.mock_smtplib_connection():
                if provide_smtp:
                    smtp_session = IrMailServer._connect__(smtp_from='"Name" <test@unknown_domain.com>')
                    message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
                    IrMailServer.send_email(message, smtp_session=smtp_session)
                else:
                    message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
                    IrMailServer.send_email(message)

            self.connect_mocked.assert_called_once()
            self.assertEqual(len(self.emails), 1)
            self.assertSMTPEmailsSent(
                smtp_from='test@unknown_domain.com',
                message_from='"Name" <test@unknown_domain.com>',
                from_filter=False,
            )

    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_mail_server')
    def test_mail_server_send_email_context_force(self):
        """ Allow to force notifications_email / bounce_address from context
        to allow higher-level apps to send values until end of mail stack
        without hacking too much models. """
        # custom notification / bounce email from context
        context_server = self.env['ir.mail_server'].create({
            'from_filter': 'context.example.com',
            'name': 'context',
            'smtp_host': 'test',
        })
        IrMailServer = self.env["ir.mail_server"].with_context(
            domain_notifications_email="notification@context.example.com",
            domain_bounce_address="bounce@context.example.com",
        )
        with self.mock_smtplib_connection():
            mail_server, smtp_from = IrMailServer._find_mail_server(email_from='"Name" <test@unknown_domain.com>')
            self.assertEqual(mail_server, context_server)
            self.assertEqual(smtp_from, "notification@context.example.com")
            smtp_session = IrMailServer._connect__(smtp_from=smtp_from)
            message = self._build_email(mail_from='"Name" <test@unknown_domain.com>')
            IrMailServer.send_email(message, smtp_session=smtp_session)

        self.assertEqual(len(self.emails), 1)
        self.assertSMTPEmailsSent(
            smtp_from="bounce@context.example.com",
            message_from='"Name" <notification@context.example.com>',
            from_filter=context_server.from_filter,
        )

        # miss-configured database, no mail servers from filter
        # match the user / notification email
        self.env['ir.mail_server'].search([]).from_filter = "random.domain"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@test.com')
            IrMailServer.with_context(domain_notifications_email='test@custom_domain.com').send_email(message)

        self.connect_mocked.assert_called_once()
        self.assertSMTPEmailsSent(
            smtp_from='test@custom_domain.com',
            message_from='"specific_user" <test@custom_domain.com>',
            from_filter='random.domain',
        )

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email_IDNA(self):
        """ Test that the mail from / recipient envelop are encoded using IDNA """
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='test@ééééééé.com')
            self.env['ir.mail_server'].send_email(message)

        self.assertEqual(len(self.emails), 1)
        self.assertSMTPEmailsSent(
            smtp_from='test@xn--9caaaaaaa.com',
            smtp_to_list=['dest@xn--example--i1a.com'],
            message_from='test@=?utf-8?b?w6nDqcOpw6nDqcOpw6k=?=.com',
            from_filter=False,
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_mail_server')
    @patch.dict(config.options, {
        "from_filter": "dummy@example.com, test.mycompany.com, dummy2@example.com",
        "smtp_server": "example.com",
    })
    def test_mail_server_config_bin(self):
        """ Test the configuration provided in the odoo-bin arguments. This config
        is used when no mail server exists. Test with and without giving a
        pre-configured SMTP session, should not impact results.

        Also check "mail.default.from_filter" parameter usage that should overwrite
        odoo-bin argument "--from-filter".
        """
        IrMailServer = self.env['ir.mail_server']

        # Remove all mail server so we will use the odoo-bin arguments
        IrMailServer.search([]).unlink()
        self.assertFalse(IrMailServer.search([]))

        for mail_from, (expected_smtp_from, expected_msg_from) in zip(
            [
                # inside "from_filter" domain
                'specific_user@test.mycompany.com',
                '"Formatted Name" <specific_user@test.mycompany.com>',
                '"Formatted Name" <specific_user@test.MYCOMPANY.com>',
                '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>',
                # outside "from_filter" domain
                'test@unknown_domain.com',
                '"Formatted Name" <test@unknown_domain.com>',
            ], [
                # inside "from_filter" domain: no rewriting
                ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com'),
                ('specific_user@test.mycompany.com', '"Formatted Name" <specific_user@test.mycompany.com>'),
                ('specific_user@test.MYCOMPANY.com', '"Formatted Name" <specific_user@test.MYCOMPANY.com>'),
                ('SPECIFIC_USER@test.mycompany.com', '"Formatted Name" <SPECIFIC_USER@test.mycompany.com>'),
                # outside "from_filter" domain: spoofing, as fallback email can be found
                ('test@unknown_domain.com', 'test@unknown_domain.com'),
                ('test@unknown_domain.com', '"Formatted Name" <test@unknown_domain.com>'),
            ]
        ):
            for provide_smtp in [False, True]:  # providing smtp session should ont impact test
                with self.subTest(mail_from=mail_from, provide_smtp=provide_smtp):
                    with self.mock_smtplib_connection():
                        if provide_smtp:
                            smtp_session = IrMailServer._connect__(smtp_from=mail_from)
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message, smtp_session=smtp_session)
                        else:
                            message = self._build_email(mail_from=mail_from)
                            IrMailServer.send_email(message)

                    self.connect_mocked.assert_called_once()
                    self.assertEqual(len(self.emails), 1)
                    self.assertSMTPEmailsSent(
                        smtp_from=expected_smtp_from,
                        message_from=expected_msg_from,
                        from_filter="dummy@example.com, test.mycompany.com, dummy2@example.com",
                    )

        # for from_filter in ICP, overwrite the one from odoo-bin
        self.env['ir.config_parameter'].sudo().set_str('mail.default.from_filter', 'icp.example.com')

        # Use an email in the domain of the config parameter "mail.default.from_filter"
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='specific_user@icp.example.com')
            IrMailServer.send_email(message)

        self.assertSMTPEmailsSent(
            smtp_from='specific_user@icp.example.com',
            message_from='specific_user@icp.example.com',
            from_filter='icp.example.com',
        )

    @mute_logger('odoo.models.unlink')
    @patch.dict(config.options, {'from_filter': 'fake.com', 'smtp_server': 'cli_example.com'})
    def test_mail_server_config_cli(self):
        """ Test the mail server configuration when the "smtp_authentication" is
        "cli". It should take the configuration from the odoo-bin argument. The
        "from_filter" of the mail server should overwrite the one set in the CLI
        arguments.
        """
        IrMailServer = self.env['ir.mail_server']
        # should be ignored by the mail server
        self.env['ir.config_parameter'].sudo().set_str('mail.default.from_filter', 'fake.com')

        server_other = IrMailServer.create([{
            'name': 'Server No From Filter',
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
            'smtp_authentication': 'cli',
            'from_filter': 'dummy@example.com, cli_example.com, dummy2@example.com',
        }])

        for mail_from, (expected_smtp_from, expected_msg_from, expected_mail_server) in zip(
            [
                # check that the CLI server take the configuration in the odoo-bin argument
                # except the from_filter which is taken on the mail server
                'test@cli_example.com',
                # other mail servers still work
                'specific_user@test.mycompany.com',
            ], [
                ('test@cli_example.com', 'test@cli_example.com', server_other),
                ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com', self.mail_server_user),
            ],
        ):
            with self.subTest(mail_from=mail_from):
                with self.mock_smtplib_connection():
                    message = self._build_email(mail_from=mail_from)
                    IrMailServer.send_email(message)

                self.assertSMTPEmailsSent(
                    smtp_from=expected_smtp_from,
                    message_from=expected_msg_from,
                    mail_server=expected_mail_server,
                )

    def test_eml_attachment_encoding(self):
        """Test that message/rfc822 attachments are encoded using 7bit, 8bit, or binary encoding per RFC."""
        IrMailServer = self.env['ir.mail_server']

        # Create a sample .eml file content
        eml_content = b"From: user@example.com\nTo: user2@example.com\nSubject: Test Email\n\nThis is a test email."
        attachments = [('test.eml', eml_content, 'message/rfc822')]

        # Build the email with the .eml attachment
        message = IrMailServer._build_email__(
            email_from='john.doe@from.example.com',
            email_to='destinataire@to.example.com',
            subject='Subject with .eml attachment',
            body='This email contains a .eml attachment.',
            attachments=attachments,
        )

        acceptable_encodings = {'7bit', '8bit', 'binary'}
        found_rfc822_part = False

        for part in message.iter_attachments():
            if part.get_content_type() == 'message/rfc822':
                found_rfc822_part = True
                # Get Content-Transfer-Encoding, defaulting to '7bit' if not present (per RFC)
                encoding = part.get('Content-Transfer-Encoding', '7bit').lower()

                self.assertIn(
                    encoding,
                    acceptable_encodings,
                    f"RFC violation: message/rfc822 attachment has Content-Transfer-Encoding '{encoding}'. "
                    f"Only 7bit, 8bit, or binary encoding is permitted per RFC 2046 Section 5.2.1."
                )

        self.assertTrue(found_rfc822_part, "No message/rfc822 attachment found in the built email")

    def test_eml_message_serialization_with_non_ascii(self):
        """Ensure an email with a message/rfc822 attachment containing non-ASCII chars can be serialized."""
        IrMailServer = self.env['ir.mail_server']

        # .eml content with non-ASCII character
        eml_content = "From: user@example.com\nTo: user2@example.com\nSubject: Test\n\nBody with é"
        attachments = [('test.eml', eml_content.encode(), 'message/rfc822')]

        message = IrMailServer._build_email__(
            email_from='john.doe@from.example.com',
            email_to='destinataire@to.example.com',
            subject='Serialization test',
            body='This email contains a .eml attachment.',
            attachments=attachments,
        )

        try:
            serialized = message.as_string().encode('utf-8')
        except UnicodeEncodeError as e:
            raise AssertionError("Email with non-ASCII .eml attachment could not be serialized") from e

        self.assertIsInstance(serialized, bytes)


if getenv('ODOO_RUNBOT') and not _openssl:
    _logger.warning("detected runbot environment but openssl not found in PATH, TestIrMailServerSMTPD will be skipped")
if getenv('ODOO_RUNBOT') and not aiosmtpd:
    _logger.warning("detected runbot environment but aiosmtpd not installed, TestIrMailServerSMTPD will be skipped")


def _find_free_local_address():
    """ Get a triple (family, address, port) on which it possible to bind
    a local tcp service. """
    addr = aiosmtpd.controller.get_localhost()  # it returns 127.0.0.1 or ::1
    family = socket.AF_INET if addr == '127.0.0.1' else socket.AF_INET6
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.bind((addr, 0))
        port = sock.getsockname()[1]
    return family, addr, port


def _smtp_authenticate(server, session, enveloppe, mechanism, data):
    """ Callback method used by aiosmtpd to validate a login/password pair. """
    result = aiosmtpd.smtp.AuthResult(success=data.password == PASSWORD.encode())
    _logger.debug("AUTH %s", "successfull" if result.success else "failed")
    return result


class Certificate:
    def __init__(self, key, cert):
        self.key = key and Path(file_path(key, filter_ext='.pem'))
        self.cert = Path(file_path(cert, filter_ext='.pem'))

    def __repr__(self):
        return f"Certificate({self.key=}, {self.cert=})"


# skip when optional dependencies are not found
@unittest.skipUnless(aiosmtpd, "aiosmtpd couldn't be imported")
@unittest.skipUnless(_openssl, "openssl not found in path")
# fail fast for timeout errors
@patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', SMTP_TIMEOUT)
# prevent the CLI from interfering with the tests
@patch.dict(config.options, {'smtp_server': ''})
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestIrMailServerSMTPD(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # aiosmtpd emits deprecation warnings because it uses its own
        # deprecated features, mute those logs.
        # https://github.com/aio-libs/aiosmtpd/issues/347
        class Session(aiosmtpd.smtp.Session):
            @property
            def login_data(self):
                return self._login_data
            @login_data.setter
            def login_data(self, value):
                self._login_data = value
        patcher = patch('aiosmtpd.smtp.Session', Session)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # aiosmtpd emits warnings for some unusual configuration, like
        # requiring AUTH on a clear-text transport. Mute those logs
        # since we also test those unusual configurations.
        warnings.filterwarnings(
            'ignore',
            "Requiring AUTH while not requiring TLS can lead to security vulnerabilities!",
            category=UserWarning
        )
        class CustomFilter(logging.Filter):
            def filter(self, record):
                if record.msg == "auth_required == True but auth_require_tls == False":
                    return False
                if record.msg == "tls_context.verify_mode not in {CERT_NONE, CERT_OPTIONAL}; this might cause client connection problems":
                    return False
                return True
        logging.getLogger('mail.log').addFilter(CustomFilter())

        # decrease aiosmtpd verbosity, odoo INFO = aiosmtpd WARNING
        logging.getLogger('mail.log').setLevel(_logger.getEffectiveLevel() + 10)

        # Get various TLS keys and certificates. CA was used to sign
        # both client and server. self_signed is... self signed.
        cls.ssl_ca, cls.ssl_client, cls.ssl_server, cls.ssl_self_signed = [
            Certificate(None, 'base/tests/ssl/ca.cert.pem'),
            Certificate('base/tests/ssl/client.key.pem',
                        'base/tests/ssl/client.cert.pem'),
            Certificate('base/tests/ssl/server.key.pem',
                        'base/tests/ssl/server.cert.pem'),
            Certificate('base/tests/ssl/self_signed.key.pem',
                        'base/tests/ssl/self_signed.cert.pem'),
        ]

        # Patch the two SMTP client classes into trusting the above CA
        class TEST_SMTP(smtplib.SMTP):
            def starttls(self, *, context):
                if context is None:
                    context = ssl._create_stdlib_context()  # what SMTP_SSL does
                    # context = ssl.create_default_context()  # what it should do
                context.load_verify_locations(cafile=str(cls.ssl_ca.cert))
                super().starttls(context=context)
        class TEST_SMTP_SSL(smtplib.SMTP_SSL):
            def _get_socket(self, *args, **kwargs):
                # self.context = ssl.create_default_context()  # what it should do
                self.context.load_verify_locations(cafile=str(cls.ssl_ca.cert))
                return super()._get_socket(*args, **kwargs)
        patcher = patch('smtplib.SMTP', TEST_SMTP)
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        patcher = patch('smtplib.SMTP_SSL', TEST_SMTP_SSL)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # fix runbot, docker uses a single ipv4 stack but it gives ::1
        # when resolving "localhost" (so stupid), use the following to
        # force aiosmtpd/odoo to bind/connect to a fixed ipv4 OR ipv6
        # address.
        family, addr, cls.port = _find_free_local_address()
        cls.localhost = getaddrinfo(addr, cls.port, family)
        cls.startClassPatcher(patch('socket.getaddrinfo', cls.getaddrinfo))

    def setUp(self):
        super().setUp()
        # reactivate sending emails during this test suite, make sure
        # NOT TO send emails using another ir.mail_server than the one
        # created in setUp!
        patcher = patch.object(IrMail_Server, '_disable_send', return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def getaddrinfo(cls, host, port, *args, **kwargs):
        """
        Resolve both "localhost" and "notlocalhost" on the ip address
        bound by aiosmtpd inside `start_smtpd`.
        """
        if host in ('localhost', 'notlocalhost') and port == cls.port:
            return cls.localhost
        return getaddrinfo(host, port, family=0, type=0, proto=0, flags=0)

    @contextlib.contextmanager
    def start_smtpd(
        self, encryption, ssl_context=None, auth_required=True, stop_on_cleanup=True
    ):
        """
        Start a smtp daemon in a background thread, stop it upon exiting
        the context manager.

        :param encryption: 'none', 'ssl' or 'starttls', the kind of
            server to start.
        :param ssl_context: the ``ssl.SSLContext`` object to use with
            'ssl' or 'starttls'.
        :param auth_required: whether the server enforces password
            authentication or not.
        """
        encryption = encryption.removesuffix('_strict')
        assert encryption in ('none', 'ssl', 'starttls')
        assert encryption == 'none' or ssl_context

        kwargs = {}
        if encryption == 'starttls':
            # for aiosmtpd.smtp.SMTP
            kwargs.update({
                'require_starttls': True,
                'tls_context': ssl_context,
            })
        elif encryption == 'ssl':
            # for aiosmtpd.controller.InetMixin
            kwargs['ssl_context'] = ssl_context
        if auth_required:
            kwargs['authenticator'] = _smtp_authenticate

        smtpd_thread = aiosmtpd.controller.Controller(
            aiosmtpd.handlers.Debugging(),
            hostname=aiosmtpd.controller.get_localhost(),
            server_hostname='localhost',
            port=self.port,
            auth_required=auth_required,
            auth_require_tls=False,
            enable_SMTPUTF8=True,
            **kwargs,
        )
        try:
            smtpd_thread.start()
            yield smtpd_thread
        finally:
            smtpd_thread.stop()

    @mute_logger('mail.log')
    def test_authentication_certificate_matrix(self):
        """
        Connect to a server that is authenticating users via a TLS
        certificate. Test the various possible configurations (missing
        cert, invalid cert and valid cert) against both a STARTTLS and
        a SSL/TLS SMTP server.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)
        ssl_context.load_verify_locations(cafile=self.ssl_ca.cert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        self_signed_key = b64encode(self.ssl_self_signed.key.read_bytes())
        self_signed_cert = b64encode(self.ssl_self_signed.cert.read_bytes())
        client_key = b64encode(self.ssl_client.key.read_bytes())
        client_cert = b64encode(self.ssl_client.cert.read_bytes())
        matrix = [
            # authentication, name, certificate, private key, error pattern
            ('login', "missing", '', '',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed"),
            ('certificate', "self signed", self_signed_cert, self_signed_key,
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed"),
            ('certificate', "valid client", client_cert, client_key, None),
        ]

        for encryption in ('starttls', 'starttls_strict', 'ssl', 'ssl_strict'):
            mail_server.smtp_encryption = encryption
            with self.start_smtpd(encryption, ssl_context, auth_required=False):
                for authentication, name, certificate, private_key, error_pattern in matrix:
                    with self.subTest(encryption=encryption, certificate=name):
                        mail_server.write({
                            'smtp_authentication': authentication,
                            'smtp_ssl_certificate': certificate,
                            'smtp_ssl_private_key': private_key,
                        })
                        if error_pattern:
                            timeout = .1 if 'timed out' in error_pattern else SMTP_TIMEOUT
                            with self.assertRaises(UserError) as error_capture, \
                                 patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', timeout):
                                mail_server.test_smtp_connection()
                            self.assertRegex(error_capture.exception.args[0], error_pattern)
                        else:
                            mail_server.test_smtp_connection()

    def test_authentication_login_matrix(self):
        """
        Connect to a server that is authenticating users via a login/pwd
        pair. Test the various possible configurations (missing pair,
        invalid pair and valid pair) against both a SMTP server without
        encryption, a STARTTLS and a SSL/TLS SMTP server.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)

        MISSING = ''
        INVALID = 'bad password'
        matrix = [
            # auth_required, password, error_pattern
            (False, MISSING, None),
            (True, MISSING, r"The server refused the sender address \(noreply@localhost\) with error .*"),
            (True, INVALID,
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed:.* timed out"),
            (True, PASSWORD, None),
        ]

        for encryption in ('none', 'starttls', 'starttls_strict', 'ssl', 'ssl_strict'):
            mail_server.smtp_encryption = encryption
            for auth_required, password, error_pattern in matrix:
                mail_server.smtp_user = password and self.user_demo.email
                mail_server.smtp_pass = password
                with self.subTest(encryption=encryption,
                                  auth_required=auth_required,
                                  password=password):
                    with self.start_smtpd(encryption, ssl_context, auth_required):
                        if error_pattern:
                            timeout = .1 if 'timed out' in error_pattern else SMTP_TIMEOUT
                            with self.assertRaises(UserError) as capture, \
                                 patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', timeout):
                                mail_server.test_smtp_connection()
                            self.assertRegex(capture.exception.args[0], error_pattern)
                        else:
                            mail_server.test_smtp_connection()

    @mute_logger('mail.log')
    def test_encryption_matrix(self):
        """
        Connect to a server on a different encryption configuration than
        the server is configured. Verify that it crashes with a good
        error message.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)

        matrix = [
            # client, server, error_pattern
            ('none', 'ssl',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed: timed out"),
            ('none', 'starttls',
                r"The server refused the sender address \(noreply@localhost\) with error .*"),
            ('starttls', 'none',
                r"An option is not supported by the server:\n "
                r"STARTTLS extension not supported by server\."),
            ('starttls', 'ssl',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed: timed out"),
            ('ssl', 'none',
                r"An SSL exception occurred\. "
                r"Check connection security type\.\n "
                r".*?wrong version number"),
            ('ssl', 'starttls',
                r"An SSL exception occurred\. "
                r"Check connection security type\.\n "
                r".*?wrong version number"),
        ]

        for client_encryption, server_encryption, error_pattern in matrix:
            with self.subTest(server_encryption=server_encryption,
                              client_encryption=client_encryption):
                mail_server.smtp_encryption = client_encryption
                with self.start_smtpd(server_encryption, ssl_context, auth_required=False):
                    timeout = .1 if 'timed out' in error_pattern else SMTP_TIMEOUT
                    with self.assertRaises(UserError) as capture, \
                         patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', timeout):
                        mail_server.test_smtp_connection()
                    self.assertRegex(capture.exception.args[0], error_pattern)

    @mute_logger('mail.log')
    def test_man_in_the_middle_matrix(self):
        """
        Simulate that a pirate was successful at intercepting the live
        traffic in between the Odoo server and the legitimate SMTP
        server.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': self.user_demo.email,
            'smtp_pass': PASSWORD,
            'smtp_ssl_certificate': b64encode(self.ssl_client.cert.read_bytes()),
            'smtp_ssl_private_key': b64encode(self.ssl_client.key.read_bytes()),
        })

        cert_good = self.ssl_server
        cert_bad = self.ssl_self_signed
        host_good = 'localhost'
        host_bad = 'notlocalhost'

        matrix = [
            # strict?, authentication, certificate, hostname, error_pattern
            (False, 'login', cert_bad, host_good, None),
            (False, 'login', cert_good, host_bad, None),
            (False, 'certificate', cert_bad, host_good, None),
            (False, 'certificate', cert_good, host_bad, None),
            (True, 'login', cert_bad, host_good,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*certificate verify failed"),
            (True, 'login', cert_good, host_bad,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*Hostname mismatch, certificate is not valid for 'notlocalhost'"),
            (True, 'certificate', cert_bad, host_good,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*certificate verify failed"),
            (True, 'certificate', cert_good, host_bad,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*CertificateError: hostname 'notlocalhost' doesn't match 'localhost'"),
        ]

        for encryption in ('starttls', 'ssl'):
            for strict, authentication, certificate, hostname, error_pattern in matrix:
                mail_server.smtp_host = hostname
                mail_server.smtp_authentication = authentication
                mail_server.smtp_encryption = encryption + ('_strict' if strict else '')
                with self.subTest(
                    encryption=encryption + ('_strict' if strict else ''),
                    authentication=authentication,
                    cert_good=certificate == cert_good,
                    host_good=hostname == host_good,
                ):
                    mitm_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    mitm_context.load_cert_chain(certificate.cert, certificate.key)
                    auth_required = authentication == 'login'
                    with self.start_smtpd(encryption, mitm_context, auth_required):
                        if error_pattern:
                            with self.assertRaises(UserError) as capture:
                                mail_server.test_smtp_connection()
                            self.assertRegex(capture.exception.args[0], error_pattern)
                        else:
                            mail_server.test_smtp_connection()
