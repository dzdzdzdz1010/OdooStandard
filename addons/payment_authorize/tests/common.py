# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.payment.tests.common import PaymentCommon


class AuthorizeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.authorize = cls._prepare_provider('authorize', update_values={
            'authorize_login': 'dummy',
            'authorize_transaction_key': 'dummy',
            'authorize_signature_key': '00000000',
            'available_currency_ids': [Command.set(cls.currency_usd.ids)]
        })

        cls.provider = cls.authorize
        cls.currency = cls.currency_usd
        cls.trans_id = '60123456789'

        # Base webhook notification structure
        cls.webhook_notification_base = {
            'notificationId': 'e4bc2a42-69e7-4cc4-bf0b-00d0c1a34c8e',
            'eventType': '',
            'eventDate': '2023-10-15T10:30:00.000Z',
            'webhookId': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            'payload': {
                'responseCode': 1,
                'authCode': '123456',
                'avsResponse': 'Y',
                'authAmount': cls.amount,
                'entityName': 'transaction',
                'id': cls.trans_id,
            },
        }

        cls.webhook_authcapture_data = {
            **cls.webhook_notification_base,
            'eventType': 'net.authorize.payment.authcapture.created',
            'payload': {
                **cls.webhook_notification_base['payload'],
                'transactionType': 'authCaptureTransaction',
                'responseReasonDescription': 'This transaction has been approved.',
            },
        }

        cls.webhook_fraud_held_data = {
            **cls.webhook_notification_base,
            'eventType': 'net.authorize.payment.fraud.held',
            'payload': {
                **cls.webhook_notification_base['payload'],
                'responseCode': 4,
                'transactionType': 'authCaptureTransaction',
                'responseReasonDescription': 'This transaction is being held for review.',
            },
        }

        cls.webhook_fraud_approved_data = {
            **cls.webhook_notification_base,
            'eventType': 'net.authorize.payment.fraud.approved',
            'payload': {
                **cls.webhook_notification_base['payload'],
                'responseCode': 1,
                'transactionType': 'authCaptureTransaction',
                'responseReasonDescription': 'This transaction has been approved after fraud review.',
            },
        }
