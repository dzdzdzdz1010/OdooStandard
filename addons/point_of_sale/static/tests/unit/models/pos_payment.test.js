import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, createPaymentLine } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { mockDate } from "@odoo/hoot-mock";
const { DateTime } = luxon;

definePosModels();

test("uiState", async () => {
    mockDate("2025-01-09 12:00:00");
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    expect(paymentline.uiState).toEqual({
        qrCode: null,
        initStateDate: new DateTime.now(),
    });
});

test("qrPaymentData", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);
    const qrCode = "https://example.com/qr-code";

    // No QR code set
    expect(paymentline.qrPaymentData).toEqual({ qrCode: null, amount: "$\u00a010.00" });

    // Set QR code
    paymentline.uiState.qrCode = qrCode;
    expect(paymentline.qrPaymentData).toEqual({ qrCode, amount: "$\u00a010.00" });

    // No pos order id set (customer display)
    paymentline.pos_order_id = null;
    expect(paymentline.qrPaymentData).toEqual({ qrCode, amount: 10 });
});

test("updateCustomerDisplayQrCode", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);
    const qrCode = "https://example.com/qr-code";

    // Update QR code
    paymentline.updateCustomerDisplayQrCode(qrCode);
    expect(paymentline.uiState.qrCode).toBe(qrCode);

    // Clear QR code
    paymentline.updateCustomerDisplayQrCode(null);
    expect(paymentline.uiState.qrCode).toBe(null);
});

test("setPaymentStatus", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // dummy status
    paymentline.canBeReversed = false;
    paymentline.setPaymentStatus("dummy_status");
    expect(paymentline.payment_status).toBe("dummy_status");
    expect(paymentline.canBeReversed).toBe(false);

    // done status + supports reversals
    card.payment_interface = { supports_reversals: true };
    paymentline.payment_status = "waitingCard";
    paymentline.canBeReversed = false;
    paymentline.setPaymentStatus("done");
    expect(paymentline.payment_status).toBe("done");
    expect(paymentline.canBeReversed).toBe(true);

    // done status + does not support reversals
    card.payment_interface = { supports_reversals: false };
    paymentline.payment_status = "waitingCard";
    paymentline.canBeReversed = false;
    paymentline.setPaymentStatus("done");
    expect(paymentline.payment_status).toBe("done");
    expect(paymentline.canBeReversed).toBe(false);

    // reversed status
    paymentline.payment_status = "reversing";
    paymentline.canBeReversed = true;
    paymentline.setPaymentStatus("reversed");
    expect(paymentline.payment_status).toBe("reversed");
    expect(paymentline.canBeReversed).toBe(false);
});

test("isDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // done
    paymentline.payment_status = "done";
    expect(paymentline.isDone()).toBe(true);

    // reversed
    paymentline.payment_status = "reversed";
    expect(paymentline.isDone()).toBe(true);

    // pending
    paymentline.payment_status = "pending";
    expect(paymentline.isDone()).toBe(false);

    // no status
    paymentline.payment_status = null;
    expect(paymentline.isDone()).toBe(true);
});

test("isProcessing", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    const processingStatuses = [
        "waiting",
        "waitingCancel",
        "waitingCard",
        "waitingScan",
        "reversing",
        "force_done",
    ];

    for (const status of processingStatuses) {
        paymentline.payment_status = status;
        expect(paymentline.isProcessing()).toBe(true);
    }

    // non-processing status
    paymentline.payment_status = "done";
    expect(paymentline.isProcessing()).toBe(false);

    // no status
    paymentline.payment_status = null;
    expect(paymentline.isProcessing()).toBe(false);
});

test("handlePaymentResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waitingCard";
    const response = paymentline.handlePaymentResponse(true);
    expect(response).toBe(true);
    expect(paymentline.payment_status).toBe("done");

    // Failed
    paymentline.payment_status = "waitingCard";
    const responseFail = paymentline.handlePaymentResponse(false);
    expect(responseFail).toBe(false);
    expect(paymentline.payment_status).toBe("retry");
});

test("handlePaymentCancelResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waitingCancel";
    const response = paymentline.handlePaymentCancelResponse(true);
    expect(response).toBe(true);
    expect(paymentline.payment_status).toBe("retry");

    // Failed - Terminal
    card.payment_method_type = "terminal";
    paymentline.payment_status = "waitingCancel";
    const responseFailTerminal = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailTerminal).toBe(false);
    expect(paymentline.payment_status).toBe("waitingCard");

    // Failed - Non-Terminal
    card.payment_method_type = "external_qr";
    paymentline.payment_status = "waitingScan";
    const responseFailNonTerminal = paymentline.handlePaymentCancelResponse(false);
    expect(responseFailNonTerminal).toBe(false);
    expect(paymentline.payment_status).toBe("waitingScan");
});

test("handlePaymentReversalResponse", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.canBeReversed = true;
    paymentline.payment_status = "reversing";
    const response = paymentline.handlePaymentReversalResponse(true);
    expect(response).toBe(true);
    expect(paymentline.payment_status).toBe("reversed");
    expect(paymentline.getAmount()).toBe(0);
    expect(paymentline.canBeReversed).toBe(false);

    // Failed
    paymentline.canBeReversed = true;
    paymentline.payment_status = "reversing";
    paymentline.amount = 10;
    const responseFail = paymentline.handlePaymentReversalResponse(false);
    expect(responseFail).toBe(false);
    expect(paymentline.payment_status).toBe("done");
    expect(paymentline.getAmount()).toBe(10);
    expect(paymentline.canBeReversed).toBe(false);
});

test("canBeAdjusted", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface + is cash
    card.is_cash_count = true;
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is bank qr code
    card.is_cash_count = false;
    card.payment_method_type = "bank_qr_code";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is not cash or bank qr code
    card.is_cash_count = false;
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface that supports adjustments
    card.payment_interface = { canBeAdjusted: () => true };
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface that does not support adjustments
    card.payment_interface = { canBeAdjusted: () => false };
    expect(paymentline.canBeAdjusted()).toBe(false);
});

test("adjustAmount", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface
    card.payment_interface = null;
    paymentline.adjustAmount(20);
    expect(paymentline.getAmount()).toBe(10);

    // payment interface that supports adjustments
    card.payment_interface = {
        sendPaymentAdjust: (uuid) => {
            const newAmount = paymentline.getAmount() + 5;
            paymentline.setAmount(newAmount);
        },
    };
    paymentline.adjustAmount(20);
    expect(paymentline.getAmount()).toBe(35); // 10 + 20 + 5
});
