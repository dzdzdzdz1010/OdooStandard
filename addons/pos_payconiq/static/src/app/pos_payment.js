import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

patch(PosPayment.prototype, {
    handlePaymentResponse(isPaymentSuccessful) {
        if (this.payment_provider !== "payconiq") {
            return super.handlePaymentResponse(...arguments);
        }

        if (isPaymentSuccessful) {
            this.setPaymentStatus("waitingScan");
            if (this.payment_method_id.payconiq_usage === "display") {
                this.updateCustomerDisplayQrCode(this.qr_code);
            }
        } else {
            this.setPaymentStatus("retry");
        }
        // Force the payment to fail to avoid auto-validating the order.
        // The payment success/failure will be handled by the Payconiq webhook - payconiq_webhook
        return false;
    },

    handlePaymentCancelResponse(isCancelSuccessful) {
        if (isCancelSuccessful) {
            this.updateCustomerDisplayQrCode(null);
        }
        return super.handlePaymentCancelResponse(...arguments);
    },
});
