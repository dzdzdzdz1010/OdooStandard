# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment methods to activate when Authorize is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'ach_direct_debit',
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
}

# Mapping of payment method codes to Authorize codes.
PAYMENT_METHODS_MAPPING = {
    'amex': 'americanexpress',
    'diners': 'dinersclub',
    'card': 'creditcard'
}

# Mapping of payment status on Authorize side to transaction statuses.
# See https://developer.authorize.net/api/reference/index.html#transaction-reporting-get-transaction-details.
TRANSACTION_STATUS_MAPPING = {
    'authorized': ['authorizedPendingCapture', 'capturedPendingSettlement'],
    'captured': ['settledSuccessfully'],
    'voided': ['voided'],
    'refunded': ['refundPendingSettlement', 'refundSettledSuccessfully'],
}

# Events which are handled by the webhook.
WEBHOOK_HANDLED_EVENTS = [
    'net.authorize.payment.authorization.created',
    'net.authorize.payment.authcapture.created',
    'net.authorize.payment.capture.created',
    'net.authorize.payment.refund.created',
    'net.authorize.payment.priorAuthCapture.created',
    'net.authorize.payment.void.created',
    'net.authorize.payment.fraud.held',
    'net.authorize.payment.fraud.declined',
    'net.authorize.payment.fraud.approved',
]

# Mapping of Authorize.Net transaction types to internal types.
TRANSACTION_TYPE_MAPPING = {
    'authOnlyTransaction': 'auth_only',
    'authCaptureTransaction': 'auth_capture',
    'priorAuthCaptureTransaction': 'prior_auth_capture',
    'captureOnlyTransaction': 'capture',
    'refundTransaction': 'refund',
    'voidTransaction': 'void',
}
