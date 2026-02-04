from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

SENSITIVE_KEYS = {'secret'}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

SUPPORTED_CURRENCIES = ['KRW']

# The codes of the payment methods to activate when Toss Payments is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    'bank_transfer',
    'mobile_phone',
}

# Mapping of payment method codes to Toss Payments codes.
PAYMENT_METHODS_MAPPING = {
    "card": "CARD",
    "bank_transfer": "TRANSFER",
    "mobile_phone": "MOBILE_PHONE",
}

# Mapping of transaction states to Toss Payments' payment statuses.
PAYMENT_STATUS_MAPPING = {'done': ('DONE'), 'canceled': ('EXPIRED'), 'error': ('ABORTED')}

# Event statuses to skip secret key verification
VERIFICATION_EXEMPT_STATUSES = ['EXPIRED', 'ABORTED']

# Events that are handled by the webhook.
HANDLED_WEBHOOK_EVENTS = ['PAYMENT_STATUS_CHANGED']
