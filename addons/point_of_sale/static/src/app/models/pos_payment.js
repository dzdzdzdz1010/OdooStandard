import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
const { DateTime } = luxon;

export class PosPayment extends Base {
    static pythonModel = "pos.payment";

    setup(vals) {
        super.setup(...arguments);
        this.payment_date = DateTime.now();
        this.amount = vals.amount || 0;
        this.ticket = vals.ticket || "";
        this.canBeReversed = false;
    }

    initState() {
        super.initState();
        this.uiState = { qrCode: null, initStateDate: DateTime.now() };
    }

    get qrPaymentData() {
        return {
            qrCode: this.uiState.qrCode,
            amount: this.pos_order_id?.currency
                ? formatCurrency(this.getAmount(), this.pos_order_id.currency)
                : this.getAmount(), // With the customer display, the pos_order_id may be undefined --> Fallback to raw amount
        };
    }

    updateCustomerDisplayQrCode(qrCode) {
        this.uiState.qrCode = qrCode;
    }

    /**
     * Use camelCase naming for consistency with other models
     */
    get payment_interface() {
        return this.payment_method_id.payment_interface;
    }

    /**
     * Use camelCase naming for consistency with other models
     */
    get payment_provider() {
        return this.payment_method_id.payment_provider;
    }

    get useTerminal() {
        return this.payment_method_id.useTerminal;
    }

    get useQr() {
        return this.payment_method_id.useQr;
    }

    get useBankQrCode() {
        return this.payment_method_id.useBankQrCode;
    }

    isSelected() {
        return this.pos_order_id?.uiState?.selected_paymentline_uuid === this.uuid;
    }

    setAmount(value) {
        this.pos_order_id.assertEditable();
        this.amount = this.pos_order_id.currency.round(parseFloat(value) || 0);
    }

    getAmount() {
        return this.amount || 0;
    }

    getPaymentStatus() {
        return this.payment_status;
    }

    setPaymentStatus(value) {
        this.payment_status = value;

        // canBeReversed
        if (value === "done") {
            this.canBeReversed = this.payment_interface?.supports_reversals || false;
        } else if (value === "reversed") {
            this.canBeReversed = false;
        }
    }

    isDone() {
        const status = this.getPaymentStatus();
        return status ? status === "done" || status === "reversed" : true;
    }

    isProcessing() {
        const status = this.getPaymentStatus();
        return status
            ? [
                  "waiting",
                  "waitingCancel",
                  "waitingCard",
                  "waitingScan",
                  "reversing",
                  "force_done",
                  "waitingCapture",
              ].includes(status)
            : false;
    }

    setCashierReceipt(value) {
        this.cashier_receipt = value;
    }

    setReceiptInfo(value) {
        this.ticket += value;
    }

    isElectronic() {
        return Boolean(this.getPaymentStatus());
    }

    // ----- Payment Request -----
    async pay() {
        this.setPaymentStatus("waiting");
        try {
            const success = await this.payment_interface.sendPaymentRequest(this.uuid);
            return this.handlePaymentResponse(success);
        } catch (error) {
            this.handlePaymentResponse(false);
            throw error;
        }
    }

    handlePaymentResponse(isPaymentSuccessful) {
        const status = isPaymentSuccessful ? "done" : "retry";
        this.setPaymentStatus(status);
        return isPaymentSuccessful;
    }

    // ----- Payment Cancel -----
    async cancelPayment(order) {
        this.setPaymentStatus("waitingCancel");
        try {
            const success = await this.payment_interface.sendPaymentCancel(order, this.uuid);
            return this.handlePaymentCancelResponse(success);
        } catch (error) {
            this.handlePaymentCancelResponse(false);
            throw error;
        }
    }

    handlePaymentCancelResponse(isCancelSuccessful) {
        if (isCancelSuccessful) {
            this.setPaymentStatus("retry");
        } else if (this.useTerminal) {
            this.setPaymentStatus("waitingCard");
        } else if (this.useQr) {
            this.setPaymentStatus("waitingScan");
        }

        return isCancelSuccessful;
    }

    // ----- Payment Reversal -----
    async reversePayment() {
        this.setPaymentStatus("reversing");
        try {
            const success = await this.payment_interface.sendPaymentReversal(this.uuid);
            return this.handlePaymentReversalResponse(success);
        } catch (error) {
            this.handlePaymentReversalResponse(false);
            throw error;
        }
    }

    handlePaymentReversalResponse(isReversalSuccessful) {
        if (isReversalSuccessful) {
            this.setAmount(0);
            this.setPaymentStatus("reversed");
        } else {
            this.setPaymentStatus("done");
            this.canBeReversed = false;
        }

        return isReversalSuccessful;
    }

    /**
     * @param {object} - refundedPaymentLine
     * Override in dependent modules to update the refund payment line with the refunded payment line
     */
    updateRefundPaymentLine(refundedPaymentLine) {}

    canBeAdjusted() {
        if (this.payment_interface) {
            return this.payment_interface.canBeAdjusted(this.uuid);
        }
        return !this.payment_method_id.is_cash_count && !this.useBankQrCode;
    }

    async adjustAmount(amount) {
        if (this.payment_interface) {
            this.amount += amount;
            await this.payment_interface.sendPaymentAdjust(this.uuid);
        }
    }
}

registry.category("pos_available_models").add(PosPayment.pythonModel, PosPayment);
