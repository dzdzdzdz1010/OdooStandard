import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    get qrPaymentData() {
        return { ...super.qrPaymentData, line: this, paymentMethod: this.payment_method_id };
    },
});
