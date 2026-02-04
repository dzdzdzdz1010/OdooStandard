import { patch } from "@web/core/utils/patch";
import { PosPaymentMethod } from "@point_of_sale/../tests/unit/data/pos_payment_method.data";

patch(PosPaymentMethod.prototype, {
    _load_pos_data_fields() {
        return [
            ...super._load_pos_data_fields(),
            "payconiq_api_key",
            "payconiq_ppid",
            "payconiq_usage",
            "payconiq_sticker_url",
            "payconiq_sticker_size",
        ];
    },

    create_payconiq_payment(id, ...args) {
        const { amount, payment_id } = args[0];
        if (amount <= 0) {
            throw new Error("Failed to create payment");
        }
        const PosPayment = this.env["pos.payment"];
        const pos_payment_id = PosPayment.search([["id", "=", payment_id]])[0];
        const pos_payment = PosPayment.read(
            [pos_payment_id],
            PosPayment._load_pos_data_fields(),
            false
        )[0];
        pos_payment.payconiq_id = "payconiq_" + pos_payment_id;
        pos_payment.qr_code = "https://example.com/qrcode/payconiq_" + pos_payment_id;

        return {
            "pos.payment": [pos_payment],
        };
    },

    cancel_payconiq_payment(id, ...args) {
        const { payment_id, force_cancel } = args[0];
        const PosPayment = this.env["pos.payment"];
        const pos_payment_id = PosPayment.search([["id", "=", payment_id]])[0];
        const pos_payment = PosPayment.read(
            [pos_payment_id],
            PosPayment._load_pos_data_fields(),
            false
        )[0];

        if (!force_cancel && pos_payment.amount < 0) {
            throw new Error(`Failed to cancel payment (ERR: ${-pos_payment.amount})`);
        }
        pos_payment.payconiq_id = null;
        pos_payment.qr_code = null;

        return {
            "pos.payment": [pos_payment],
        };
    },
});

PosPaymentMethod._records.push(
    {
        id: 4,
        name: "Payconiq Display",
        payconiq_sticker_size: "S",
        payconiq_usage: "display",
        is_cash_count: false,
        is_online_payment: false,
        payment_provider: "payconiq",
        payment_method_type: "external_qr",
        payconiq_api_key: "display_api_key",
        payconiq_ppid: "display_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 3,
        default_qr: false,
    },
    {
        id: 5,
        name: "Payconiq Sticker 1",
        payconiq_sticker_size: "M",
        payconiq_usage: "sticker",
        is_cash_count: false,
        is_online_payment: false,
        payment_provider: "payconiq",
        payment_method_type: "external_qr",
        payconiq_api_key: "sticker_api_key",
        payconiq_ppid: "sticker_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 4,
        default_qr: false,
    },
    {
        id: 6,
        name: "Payconiq Sticker 2",
        payconiq_sticker_size: "L",
        payconiq_usage: "sticker",
        is_cash_count: false,
        is_online_payment: false,
        payment_provider: "payconiq",
        payment_method_type: "external_qr",
        payconiq_api_key: "sticker_api_key",
        payconiq_ppid: "sticker_profile_id",
        split_transactions: false,
        type: "bank",
        image: false,
        sequence: 5,
        default_qr: false,
    }
);
