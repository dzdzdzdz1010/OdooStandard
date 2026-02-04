import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    canSendPaymentRequest({ paymentMethod, paymentline }) {
        paymentMethod = paymentMethod || paymentline.payment_method_id;
        if (paymentMethod.payment_provider !== "payconiq") {
            return super.canSendPaymentRequest(...arguments);
        }

        // Display
        if (paymentMethod.payconiq_usage === "display") {
            return { status: true, message: "" };
        }

        // Sticker
        if (paymentMethod.payconiq_usage === "sticker") {
            const hasProcessingPaymentSameSticker = this.payment_ids.some(
                (pl) =>
                    pl.payment_method_id.id === paymentMethod.id &&
                    pl.uuid !== paymentline?.uuid &&
                    pl.isProcessing()
            );
            if (hasProcessingPaymentSameSticker) {
                return {
                    status: false,
                    message: _t("This sticker is already processing another payment."),
                };
            }
            return { status: true, message: "" };
        }

        // Unknown usage
        return super.canSendPaymentRequest(...arguments);
    },
});
