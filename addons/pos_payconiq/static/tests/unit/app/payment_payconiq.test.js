import { test, expect, describe, animationFrame } from "@odoo/hoot";
import {
    setupPosEnv,
    getFilledOrder,
    createPaymentLine,
    activateMountingDialogs,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { click } from "@odoo/hoot-dom";

definePosModels();

describe("sendPaymentRequest", () => {
    test("failed to create payconiq payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = { amount: -1, payment_status: "pending" };
        const paymentlineDisplay = createPaymentLine(store, order, display, opts);
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts);
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            let failed = false;
            try {
                await paymentline.payment_interface.sendPaymentRequest(paymentline.uuid);
            } catch {
                failed = true;
            }

            expect(failed).toBe(true);
            expect(paymentline.payconiq_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();
            expect(store.qrCode).toBeEmpty();

            // Payment status is updated inside `handlePaymentResponse`, so it remains unchanged here
            expect(paymentline.payment_status).toBe("pending");
        }
    });

    test("success to create payconiq payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = { payment_status: "pending" };
        const paymentlineDisplay = createPaymentLine(store, order, display, opts);
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts);
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            store.qrCode = null; // Reset QR code between iterations

            const result = await paymentline.payment_interface.sendPaymentRequest(paymentline.uuid);
            const payconiqId = "payconiq_" + paymentline.id;
            const qrCodeUrl = `https://example.com/qrcode/${payconiqId}`;

            expect(result).toBe(true);
            expect(paymentline.payconiq_id).toBe(payconiqId);
            expect(paymentline.qr_code).toBe(qrCodeUrl);

            if (paymentline.id === paymentlineDisplay.id) {
                expect({ ...store.qrCode, closer: typeof store.qrCode?.closer }).toEqual({
                    paymentline: paymentlineDisplay,
                    closer: "function",
                });
            } else {
                expect(store.qrCode).toBeEmpty();
            }

            // Payment status is updated inside `handlePaymentResponse`, so it remains unchanged here
            expect(paymentline.payment_status).toBe("pending");
        }
    });
});

describe("sendPaymentCancel", () => {
    test("failed to cancel payconiq payment (ERR: 400)", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = (payconiq_id) => ({
            amount: -400, // To trigger ERR: 400
            payment_status: "waitingScan",
            payconiq_id: payconiq_id,
            qr_code: `https://example.com/qrcode/${payconiq_id}`,
        });
        const displayTestId = "payconiq_1";
        const stickerTestId = "payconiq_2";
        const paymentlineDisplay = createPaymentLine(store, order, display, opts(displayTestId));
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts(stickerTestId));
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            const result = await paymentline.payment_interface.sendPaymentCancel(
                order,
                paymentline.uuid
            );
            expect(result).toBe(true);
            expect(paymentline.payconiq_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();

            // Payment status is updated inside `handlePaymentCancelResponse`, so it remains unchanged here
            expect(paymentline.payment_status).toBe("waitingScan");

            // ------
            // Asserting store.qrCode is not needed since we should not be able to send the cancel request while the qrCode is shown
            // Any button that triggers sendPaymentCancel is behind the QRPopup
        }
    });

    test("failed to cancel payconiq payment (ERR: 422)", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = (payconiq_id) => ({
            amount: -422, // To trigger ERR: 422
            payment_status: "waitingScan",
            payconiq_id: payconiq_id,
            qr_code: `https://example.com/qrcode/${payconiq_id}`,
        });
        const displayTestId = "payconiq_1";
        const stickerTestId = "payconiq_2";
        const paymentlineDisplay = createPaymentLine(store, order, display, opts(displayTestId));
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts(stickerTestId));
        const paymentlines = [paymentlineDisplay, paymentlineSticker];
        const getPayconiqId = (pl) =>
            pl.id === paymentlineDisplay.id ? displayTestId : stickerTestId;
        const qrCodeUrl = (pl) =>
            pl.id === paymentlineDisplay.id
                ? `https://example.com/qrcode/${displayTestId}`
                : `https://example.com/qrcode/${stickerTestId}`;

        await activateMountingDialogs(store.env);
        for (const paymentline of paymentlines) {
            // ---- Click on 'Close' button ----
            const promiseResultClose = paymentline.payment_interface.sendPaymentCancel(
                order,
                paymentline.uuid
            );

            await animationFrame();
            await click(".modal-footer .btn-primary");

            const resultClose = await promiseResultClose;
            expect(resultClose).toBe(false);
            expect(paymentline.payconiq_id).toBe(getPayconiqId(paymentline));
            expect(paymentline.qr_code).toBe(qrCodeUrl(paymentline));

            // Payment status is updated inside `handlePaymentCancelResponse`, so it remains unchanged here
            expect(paymentline.payment_status).toBe("waitingScan");

            // ---- Force cancel ----
            const promiseResultForce = paymentline.payment_interface.sendPaymentCancel(
                order,
                paymentline.uuid
            );

            await animationFrame();
            await click(".modal-footer .btn-secondary");

            const resultForce = await promiseResultForce;
            expect(resultForce).toBe(true);
            expect(paymentline.payconiq_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();

            // Payment status is updated inside `handlePaymentCancelResponse`, so it remains unchanged here
            expect(paymentline.payment_status).toBe("waitingScan");

            // ------
            // Asserting store.qrCode is not needed since we should not be able to send the cancel request while the qrCode is shown
            // Any button that triggers sendPaymentCancel is behind the QRPopup
        }
    });

    test("success to cancel payconiq payment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const display = store.models["pos.payment.method"].get(4);
        const sticker = store.models["pos.payment.method"].get(5);

        const opts = (payconiq_id) => ({
            payment_status: "waitingScan",
            payconiq_id: payconiq_id,
            qr_code: `https://example.com/qrcode/${payconiq_id}`,
        });
        const displayTestId = "payconiq_1";
        const stickerTestId = "payconiq_2";
        const paymentlineDisplay = createPaymentLine(store, order, display, opts(displayTestId));
        const paymentlineSticker = createPaymentLine(store, order, sticker, opts(stickerTestId));
        const paymentlines = [paymentlineDisplay, paymentlineSticker];

        for (const paymentline of paymentlines) {
            const result = await paymentline.payment_interface.sendPaymentCancel(
                order,
                paymentline.uuid
            );
            expect(result).toBe(true);
            expect(paymentline.payconiq_id).toBeEmpty();
            expect(paymentline.qr_code).toBeEmpty();

            // Payment status is updated inside `handlePaymentCancelResponse`, so it remains unchanged here
            expect(paymentline.payment_status).toBe("waitingScan");

            // ------
            // Asserting store.qrCode is not needed since we should not be able to send the cancel request while the qrCode is shown
            // Any button that triggers sendPaymentCancel is behind the QRPopup
        }
    });
});
