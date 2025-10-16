import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { enhancedButtons } from "@point_of_sale/app/components/numpad/numpad";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";

export class PaymentScreenPaymentLines extends Component {
    static template = "point_of_sale.PaymentScreenPaymentLines";
    static components = { PriceFormatter };
    static props = {
        paymentLines: { type: Array, optional: true },
        deleteLine: Function,
        selectLine: Function,
        sendForceDone: Function,
        sendForceCancel: Function,
        sendPaymentCancel: Function,
        sendPaymentRequest: Function,
        sendPaymentReverse: Function,
        updateSelectedPaymentline: Function,
        isRefundOrder: Boolean,
    };

    setup() {
        this.ui = useService("ui");
        this.pos = usePos();
        this.dialog = useService("dialog");

        this.forceCancelPayments();
    }

    forceCancelPayments() {
        for (const payment of this.props.paymentLines) {
            if (this.pos.paymentsToForceCancel.has(payment.id)) {
                this.props.sendForceCancel(payment);
                this.pos.paymentsToForceCancel.delete(payment.id);
            }
        }
    }

    async selectLine(paymentline) {
        this.props.selectLine(paymentline.uuid);
        if (this.ui.isSmall) {
            this.dialog.add(NumberPopup, {
                title: _t("New amount"),
                buttons: enhancedButtons(),
                startingValue: this.env.utils.formatCurrency(paymentline.getAmount(), false),
                getPayload: (num) => {
                    this.props.updateSelectedPaymentline(parseFloat(num));
                },
            });
        }
    }

    showQrCode(line) {
        this.pos.displayQrCode(line);
    }

    /**
     * Get the payment action state for the given payment line.
     * @returns {PaymentActionState}
     *
     * @typedef {Object} PaymentAction
     * @property {string} id                      - Unique identifier for the action.
     * @property {string} label                   - Text displayed on the action button.
     * @property {string} [title]                 - Title of the button. If not provided, `label` is used.
     * @property {Function} action                - Callback executed when the button is clicked.
     * @property {string} classes                 - Additional CSS classes to apply to the button.
     * @property {string} severity                - Bootstrap color variant (e.g., "danger", "warning", "success", "info", ...).
     * @property {boolean} [show]                 - Condition to determine if the action should be displayed (show by default).
     *
     * @typedef {Object} PaymentActionState
     * @property {string} id                      - Unique identifier for the payment state.
     * @property {string} title                   - Title of the payment status section.
     * @property {Array<PaymentAction>} actions   - Actions available for the current payment state.
     * @property {string} [icon]                  - Optional icon representing the payment state.
     *
     * @type {PaymentActionState}
     */
    getPaymentActionState(line) {
        const status = line.payment_status;
        const isRefund = this.props.isRefundOrder;
        const camelToSnakeCase = (id) => id.replace(/([A-Z])/g, "_$1").toLowerCase();
        const SPINNER_ICON = "fa fa-circle-o-notch fa-spin";
        const ACTIONS = {
            send: {
                id: "send",
                label: _t("Send"),
                title: _t("Send Payment Request"),
                action: () => this.props.sendPaymentRequest(line),
                severity: "primary",
            },

            retry: {
                id: "retry",
                label: _t("Retry"),
                title: _t("Retry Payment Request"),
                action: () => this.props.sendPaymentRequest(line),
                severity: "primary",
            },

            refund: {
                id: "refund",
                label: _t("Refund"),
                title: _t("Send Refund Request"),
                action: () => this.props.sendPaymentRequest(line),
                severity: "primary",
            },

            forceDone: {
                id: "force_done",
                label: _t("Force done"),
                action: () => this.props.sendForceDone(line),
                severity: "warning",
            },

            cancel: {
                id: "cancel",
                label: _t("Cancel"),
                title: _t("Send Cancel Request"),
                action: () => this.props.sendPaymentCancel(line),
                severity: "danger",
                show: !isRefund,
            },

            forceCancel: {
                id: "force_cancel",
                label: _t("Force Cancel"),
                action: () => this.props.sendForceCancel(line),
                severity: "danger",
            },

            reverse: {
                id: "reverse",
                label: _t("Reverse"),
                title: _t("Send Reverse Request"),
                action: () => this.props.sendPaymentReverse(line),
                severity: "warning",
                show: line.canBeReversed,
            },
        };
        const state = { id: "unknown", title: "", actions: [] };

        // --- Pending
        if (status === "pending") {
            state.id = "pending";
            state.title = _t("Payment request pending");
            state.actions = [ACTIONS.send];
        }

        // --- Retry
        else if (status === "retry") {
            state.id = "retry";
            state.title = _t("Transaction cancelled");
            state.actions = [ACTIONS.retry];
        }

        // --- Force done
        if (status === "force_done") {
            state.id = "force_done";
            state.title = _t("Connection error");
            state.actions = [ACTIONS.forceDone];
        }

        // --- Waiting customer action
        if (["waitingCard", "waitingScan"].includes(status)) {
            const titles = {
                waitingCard: _t("Waiting for card"),
                waitingScan: _t("Waiting for the customer to scan the QR Code"),
            };

            state.id = isRefund ? "waiting_refund" : camelToSnakeCase(status);
            state.title = isRefund ? _t("Refund in process") : titles[status];
            state.icon = SPINNER_ICON;
            state.actions = [ACTIONS.forceDone, ACTIONS.cancel];
        }

        // --- Request sent
        if (["waiting", "waitingCancel", "waitingCapture"].includes(status)) {
            state.id = camelToSnakeCase(status);
            state.title = _t("Request sent");
            state.icon = SPINNER_ICON;
            state.actions = [
                { ...ACTIONS.forceDone, show: status === "waiting" },
                { ...ACTIONS.forceCancel, show: status === "waitingCancel" },
            ];
        }

        // --- Reversing
        if (status === "reversing") {
            state.id = "reversing";
            state.title = _t("Reversal request sent to terminal");
            state.icon = SPINNER_ICON;
            state.actions = [];
        }

        // --- Done
        if (status === "done") {
            state.id = isRefund ? "refunded" : "paid";
            state.title = isRefund ? _t("Refund Successful") : _t("Payment Successful");
            state.actions = [ACTIONS.reverse];
        }

        // --- Reversed
        if (status === "reversed") {
            state.id = "reversed";
            state.title = _t("Payment reversed");
            state.actions = [];
        }

        // --- Refund available
        if (!status && isRefund && line.payment_interface) {
            state.id = "refund_available";
            state.title = _t("Refund available");
            state.actions = [ACTIONS.refund];
        }

        return state;
    }
}
