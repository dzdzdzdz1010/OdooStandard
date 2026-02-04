import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentPayconiq extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.supports_refunds = false;
    }

    async sendPaymentRequest(uuid) {
        const order = this.pos.getOrder();
        const line = order.getPaymentlineByUuid(uuid);
        await this.pos.syncAllOrders({ orders: [order] });

        const description = _t(
            "Payment at %s\nPOS %s",
            this.pos.company.name,
            this.pos.config.name
        );
        await this.pos.data.callRelated(
            "pos.payment.method",
            "create_payconiq_payment",
            [line.payment_method_id.id],
            {
                payment_id: line.id,
                amount: line.amount,
                currency: this.pos.currency.name,
                posId: this.pos.config.id,
                shopName: this.pos.config.name,
                paymentMethodId: line.payment_method_id.id,
                description: description,
                usage: line.payment_method_id.payconiq_usage,
            }
        );

        if (line.payment_method_id.payconiq_usage === "display") {
            this.pos.displayQrCode(line);
        }
        return true;
    }

    async sendPaymentCancel(order, uuid) {
        const line = order.getPaymentlineByUuid(uuid);
        const blockingErrorCodes = [422];

        const askForceCancel = async (errorCode) => {
            let message = _t(
                "The cancellation could not be performed. Are you sure you want to force the cancellation?"
            );
            if (errorCode === 422) {
                message = _t(
                    "The customer is currently completing the payment and it cannot be cancelled right now.\n" +
                        "If you need to cancel, please ask the customer to do so on their device or force the cancellation."
                );
            }
            return new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Oh snap !"),
                    body: message,
                    confirmLabel: _t("Close"),
                    confirm: () => resolve(false),
                    cancelLabel: _t("Force Cancel"),
                    cancel: () => resolve(true),
                    dismiss: () => resolve(false),
                });
            });
        };

        try {
            await this.pos.syncAllOrders({ orders: [order] });
            await this.pos.data.callRelated(
                "pos.payment.method",
                "cancel_payconiq_payment",
                [line.payment_method_id.id],
                { payment_id: line.id }
            );
            return true;
        } catch (error) {
            const message = error.data?.message || "";
            const errorCode = blockingErrorCodes.find((code) => message.includes(`ERR: ${code}`));
            const forceCancel = errorCode ? await askForceCancel(errorCode) : true;

            if (forceCancel) {
                await this.pos.data.callRelated(
                    "pos.payment.method",
                    "cancel_payconiq_payment",
                    [line.payment_method_id.id],
                    { payment_id: line.id, force_cancel: forceCancel }
                );
            }

            return forceCancel;
        }
    }
}

registry.category("pos_payment_providers").add("payconiq", PaymentPayconiq);
