/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

// -------------------------------
// Generic
// -------------------------------
export function wait(delay) {
    return {
        content: `wait for ${delay} ms`,
        trigger: "body",
        run: async () => await new Promise((resolve) => setTimeout(resolve, delay)),
    };
}

// -------------------------------
// Payconiq dialogs
// -------------------------------
export function closePayconiqApiErrorDialog(statusCode) {
    return [
        {
            content:
                "check that an error dialog due to the creation of the Payconiq payment is displayed",
            trigger: `.o_alert_dialog .modal-body:contains("(ERR: ${statusCode})")`,
        },
        Dialog.confirm(),
    ].flat();
}

export function payconiqAskForceCancelDialogIsShown() {
    return {
        content: "check that the confirmation dialog to force cancel is displayed",
        trigger: `.o_confirmation_dialog .modal-body:contains("The customer is currently completing the payment and it cannot be cancelled right now.")`,
    };
}

export function closeStickerAlreadyInUseErrorDialog() {
    return [
        {
            content: "check that an error dialog due to the sticker already in use is displayed",
            trigger: `.o_alert_dialog .modal-body:contains("This sticker is already processing another payment.")`,
        },
        Dialog.confirm(),
    ].flat();
}

// -------------------------------
// Notifications
// -------------------------------
export function notifiedOrderPartiallyPaid(orderName) {
    return {
        content: `check that a notification for partially paid order ${orderName} is displayed`,
        trigger: `.o_notification:has(.o_notification_bar.bg-success):has(.o_notification_content:contains('The order ${orderName} has been partially paid.')) .o_notification_close`,
        run: "click",
    };
}

export function notifiedOrderFullyPaid(orderName) {
    return {
        content: `check that a notification for fully paid order ${orderName} is displayed`,
        trigger: `.o_notification:has(.o_notification_bar.bg-success):has(.o_notification_content:contains('The order ${orderName} has been fully paid.')) .o_notification_close`,
        run: "click",
    };
}

export function notifiedPaymentReceived() {
    return {
        content: "check that a notification for received payment is displayed",
        trigger: `.o_notification:has(.o_notification_bar.bg-success):has(.o_notification_content:contains('Payment received')) .o_notification_close`,
        run: "click",
    };
}

export function notifiedPayconiqPaymentError(message) {
    return {
        content: "close the notification",
        trigger: `.o_notification:has(.o_notification_bar.bg-warning):has(.o_notification_content:contains('${message}')) .o_notification_close`,
        run: "click",
    };
}

// -------------------------------
// Payconiq payment callbacks
// -------------------------------
export function mockCallbackPayconic(status, fromEnd = 1) {
    return [
        wait(200),
        {
            content: "mock scan QR code",
            trigger: "body",
            run: async () => {
                const orm = posmodel.env.services.orm;
                const response = await orm.searchRead("pos.payment", [], ["payconiq_id"], {
                    limit: fromEnd,
                    order: "id desc",
                });
                if (!response || response.length < fromEnd) {
                    throw new Error("Not enough Payconiq payments found to mock scan QR code");
                }

                fetch("/webhook/payconiq?mode=test", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        paymentId: response[fromEnd - 1].payconiq_id,
                        status: status,
                    }),
                });
            },
        },
        wait(200),
    ].flat();
}

// -------------------------------
// Console error mocking
// -------------------------------
/**
 * Temporarily disables `console.error` during a test run.
 *
 * This helper is used when mocking failed Payconiq API responses.
 * In that scenario, the error is intentionally thrown and bubbles up,
 * which would normally trigger `console.error`.
 *
 * In the test environment, logging an error causes the backend to record
 * the error and marks the tour as failed, even though the failure is expected
 * and the test itself is successful.
 *
 * This setup step silences `console.error` to prevent false-negative test
 * failures caused by expected Payconiq HTTP errors.
 *
 * @param {Object} memo
 *   Mutable object used to store the original `console.error` reference
 *   so it can be restored during teardown.
 */
export function setupPayconiqErrorHttp(memo) {
    return {
        content: "setup Payconiq error http mocking",
        trigger: "body",
        run: () => {
            memo.consoleError = console.error;
            console.error = () => {};
        },
    };
}

/**
 * Restores the original `console.error` after Payconiq HTTP error mocking.
 *
 * This teardown step re-enables normal error logging once the test is done,
 * ensuring that real errors are logged correctly outside of the mocked
 * Payconiq failure scenario.
 *
 * @param {Object} memo
 *   Mutable object used to store the original `console.error` reference.
 */
export function teardownPayconiqErrorHttp(memo) {
    return {
        content: "teardown Payconiq error http mocking",
        trigger: "body",
        run: () => {
            console.error = memo.consoleError;
            memo.consoleError = null;
        },
    };
}
