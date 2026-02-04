import logging
from json import JSONDecodeError

from odoo import _
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)

_logger = logging.getLogger(__name__)


def assert_payconiq_http_success(response, extra_errors=None):
    """
    Checks the Payconiq API response for errors and raises appropriate exceptions.

    The mapping used is PAYCONIQ_ERRORS merged with any overrides provided
    via `extra_errors` (overrides take precedence).

    :param response: requests.Response-like object
    :param extra_errors: Optional[Dict[int, Tuple[str, Exception]]]
    """

    errors = {
        400: (
            _("Invalid request to Payconiq. Please check the request details."),
            MissingError,
        ),
        401: (
            _("Authentication with Payconiq failed. Please verify your API key."),
            AccessDenied,
        ),
        403: (
            _("Access denied. Please check your Payconiq API permissions."),
            AccessDenied,
        ),
        404: (
            _("Merchant profile not found on Payconiq. Please check your Payment Profile ID."),
            UserError,
        ),
        422: (
            _("Unable to process the request. Please verify your configuration or try again later."),
            ValidationError,
        ),
        429: (
            _("Rate limit reached with Payconiq. Please wait and try again."),
            AccessDenied,
        ),
        500: (
            _("Payconiq is currently unavailable. Please try again later."),
            AccessError,
        ),
        503: (
            _("Payconiq is currently unavailable. Please try again later."),
            AccessError,
        ),
        **(extra_errors or {}),
    }

    if response.status_code in errors:
        error_message, exception_class = errors[response.status_code]
        try:
            error_data = response.json()
        except JSONDecodeError:
            error_data = {}
        code = error_data.get("code", "")
        msg = error_data.get("message", "")

        log_msg = f"Payconiq: status_code:{response.status_code}: "
        if code:
            log_msg += f"code:{code} "
        log_msg += f"{msg or error_message}"
        _logger.error(log_msg)

        exception_msg = f"{error_message} (ERR: {response.status_code}"
        if code:
            exception_msg += f" - {code}"
        exception_msg += ")"
        raise exception_class(exception_msg)

    response.raise_for_status()
