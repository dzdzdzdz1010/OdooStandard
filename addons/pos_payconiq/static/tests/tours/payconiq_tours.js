import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Payconiq from "./utils/payconiq_utils.js";
import { registry } from "@web/core/registry";

const initOrder = () =>
    [
        ProductScreen.clickDisplayedProduct("Desk Pad"),
        Numpad.click("Price"),
        Numpad.enterValue("10"),
        Payconiq.wait(200),
        ProductScreen.clickPayButton(),
    ].flat();

const memo = {};
registry.category("web_tour.tours").add("payconiq_failed_to_create_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Add a new payment line using Payconiq but the request return an error 401
            Payconiq.setupPayconiqErrorHttp(memo),
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            Payconiq.closePayconiqApiErrorDialog(401),
            PaymentScreen.hasActionState("retry"),

            // Retry to send the payment via the action state button
            PaymentScreen.clickRetryButton(),
            Payconiq.closePayconiqApiErrorDialog(401),
            Payconiq.teardownPayconiqErrorHttp(memo),

            // Delete the faulty payment line
            PaymentScreen.clickPaymentlineDelButton("Payconiq - Display", "10.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("payconiq_can_send_request", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Order 1001 - Display [A]
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1001 - Display [B]
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1001 - Sticker 1 [C]
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 1"),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR + Not created => Order 1001 - Sticker 1 [D]
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 1"),
            Payconiq.closeStickerAlreadyInUseErrorDialog(),
            PaymentScreen.countPaymentlinesIs(3),

            // Cancel C and retry creating D
            PaymentScreen.clickPaymentline("Payconiq - Sticker 1", undefined, 3),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 1"),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR => Retry C
            PaymentScreen.clickPaymentline("Payconiq - Sticker 1", undefined, 3),
            PaymentScreen.clickRetryButton(),
            Payconiq.closeStickerAlreadyInUseErrorDialog(),
            PaymentScreen.hasActionState("retry"),

            // Order 1001 - Sticker 2 [E]
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 2"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1002 - Display [F]
            Chrome.createFloatingOrder(),
            initOrder(),
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR + Not created =>  Order 1002 - Sticker 2 [G]
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 2"),
            Payconiq.closeStickerAlreadyInUseErrorDialog(),
            PaymentScreen.countPaymentlinesIs(1),

            // Cancel E and retry creating G
            Chrome.clickFloatingOrder("1001"),
            PaymentScreen.clickPaymentline("Payconiq - Sticker 2", undefined, 5),
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),
            Chrome.clickFloatingOrder("1002"),
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 2"),
            PaymentScreen.hasActionState("waiting_scan"),

            // ERROR => Retry E
            Chrome.clickFloatingOrder("1001"),
            PaymentScreen.clickPaymentline("Payconiq - Sticker 2", undefined, 5),
            PaymentScreen.clickRetryButton(),
            Payconiq.closeStickerAlreadyInUseErrorDialog(),
            PaymentScreen.hasActionState("retry"),
        ].flat(),
});

registry.category("web_tour.tours").add("payconiq_show_qr_code", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Display waiting
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.qrPopupIsShown("10.00"),
            PaymentScreen.closeQrPopup(),
            Payconiq.wait(200),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("10.00"),
            PaymentScreen.closeQrPopup(),

            // Display cancel
            PaymentScreen.clickCancelButton(),
            PaymentScreen.showQrPopupIsDisabled(),

            // Display retry
            Payconiq.wait(200),
            PaymentScreen.enterPaymentLineAmount("Payconiq - Display", "2"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.qrPopupIsShown("2.00"),
            PaymentScreen.closeQrPopup(),
            Payconiq.wait(200),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("2.00"),
            PaymentScreen.closeQrPopup(),

            // Sticker waiting
            PaymentScreen.clickPaymentMethod("Payconiq - Sticker 1"),
            PaymentScreen.qrPopupIsNotShown(),
            Payconiq.wait(200),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("10.00"),
            PaymentScreen.closeQrPopup(),

            // Sticker cancel
            PaymentScreen.clickCancelButton(),
            PaymentScreen.showQrPopupIsDisabled(),

            // Sticker retry
            Payconiq.wait(200),
            PaymentScreen.enterPaymentLineAmount("Payconiq - Sticker 1", "3"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.qrPopupIsNotShown(),
            Payconiq.wait(200),
            PaymentScreen.showQrPopup({ selected: true }),
            PaymentScreen.qrPopupIsShown("3.00"),
            PaymentScreen.closeQrPopup(),

            // Open display sticker without selecting it and pay for the sticker
            Payconiq.wait(200),
            PaymentScreen.showQrPopup({ name: "Payconiq - Display" }),
            PaymentScreen.qrPopupIsShown("2.00"),
            Payconiq.mockCallbackPayconic("SUCCEEDED"),
            PaymentScreen.qrPopupIsShown("2.00"),

            // Pay now for the display
            Payconiq.mockCallbackPayconic("SUCCEEDED", 2),
            PaymentScreen.qrPopupIsNotShown(),

            // Payment failed close qr
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.qrPopupIsShown("5.00"),
            Payconiq.mockCallbackPayconic("FAILED"),
            PaymentScreen.qrPopupIsNotShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("payconiq_success_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Order 1001 - Display 5€ [A]
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.clickCancelButton(),
            Payconiq.wait(200),
            PaymentScreen.enterPaymentLineAmount("Payconiq - Display", "5"),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Order 1001 - Display 2€ [B]
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.clickCancelButton(),
            Payconiq.wait(200),
            PaymentScreen.enterPaymentLineAmount("Payconiq - Display", "2"),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line A while being on another payment line - notified
            Payconiq.mockCallbackPayconic("SUCCEEDED", 2),
            Payconiq.notifiedPaymentReceived(),
            PaymentScreen.clickPaymentline("Payconiq - Display", "5"),
            PaymentScreen.hasActionState("paid"),
            PaymentScreen.clickPaymentline("Payconiq - Display", "2"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line B
            Payconiq.mockCallbackPayconic("SUCCEEDED", 1),
            PaymentScreen.hasActionState("paid"),

            // Order 1001 - Display 3€ (fully paid) [C]
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line C - Autovalidate order
            Payconiq.mockCallbackPayconic("SUCCEEDED"),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),

            // Order 1002 - Display 5€ [D]
            initOrder(),
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.clickCancelButton(),
            Payconiq.wait(200),
            PaymentScreen.enterPaymentLineAmount("Payconiq - Display", "5"),
            PaymentScreen.hasActionState("retry"),
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line D while on another order - notified
            Chrome.createFloatingOrder(),
            Payconiq.mockCallbackPayconic("SUCCEEDED"),
            Payconiq.notifiedOrderPartiallyPaid("1002"),

            // Order 1002 - Display 5€ (fully paid) [E]
            Chrome.clickFloatingOrder("1002"),
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Pay payment line E while on another order - notified + NOT autovalidate
            Chrome.clickFloatingOrder("1003"),
            Payconiq.mockCallbackPayconic("SUCCEEDED"),
            Payconiq.notifiedOrderFullyPaid("1002"),
            Chrome.clickFloatingOrder("1002"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),

            // Order 1003 - Force done payment [F] - autovalidate
            FeedbackScreen.clickNextOrder(),
            initOrder(),
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),
            PaymentScreen.clickForceDoneButton(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("payconiq_failed_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Simulate a AUTHORIZATION_FAILED payment from Payconiq side
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Payconiq.mockCallbackPayconic("AUTHORIZATION_FAILED"),
            PaymentScreen.hasActionState("retry"),
            Payconiq.notifiedPayconiqPaymentError("Payment failed"),

            // Simulate a FAILED payment from Payconiq side
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Payconiq.mockCallbackPayconic("FAILED"),
            PaymentScreen.hasActionState("retry"),
            Payconiq.notifiedPayconiqPaymentError("Payment failed"),

            // Simulate a EXPIRED payment from Payconiq side
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Payconiq.mockCallbackPayconic("EXPIRED"),
            PaymentScreen.hasActionState("retry"),
            Payconiq.notifiedPayconiqPaymentError("Payment expired"),

            // Simulate a CANCELLED payment from Payconiq side
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.hasActionState("waiting_scan"),
            Payconiq.mockCallbackPayconic("CANCELLED"),
            PaymentScreen.hasActionState("retry"),
            Payconiq.notifiedPayconiqPaymentError("Payment cancelled"),

            // Failed while not current order
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            Chrome.createFloatingOrder(),
            Payconiq.mockCallbackPayconic("FAILED"),
            Payconiq.notifiedPayconiqPaymentError("A payment for order 1001 has failed."),
        ].flat(),
});

registry.category("web_tour.tours").add("payconiq_failed_to_cancel_payment_error_422", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Add a new payment line using Payconiq
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Cancel the payment with an error 422 thrown --> ask to force cancel the payment
            PaymentScreen.clickCancelButton(),
            Payconiq.payconiqAskForceCancelDialogIsShown(),
            Dialog.confirm("Close"),
            PaymentScreen.hasActionState("waiting_scan"),

            // Force cancel the payment
            PaymentScreen.clickCancelButton(),
            Payconiq.payconiqAskForceCancelDialogIsShown(),
            Dialog.confirm("Force Cancel", ".btn-secondary"),
            PaymentScreen.hasActionState("retry"),

            // Can retry to send the payment
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),
        ].flat(),
});

registry.category("web_tour.tours").add("payconiq_failed_to_cancel_payment_error_429", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            initOrder(),

            // Add a new payment line using Payconiq
            PaymentScreen.clickPaymentMethod("Payconiq - Display"),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),

            // Cancel the payment with an error 429 thrown --> caught and ignore the error
            PaymentScreen.clickCancelButton(),
            PaymentScreen.hasActionState("retry"),

            // Can retry to send the payment
            PaymentScreen.clickRetryButton(),
            PaymentScreen.closeQrPopup(),
            PaymentScreen.hasActionState("waiting_scan"),
        ].flat(),
});
