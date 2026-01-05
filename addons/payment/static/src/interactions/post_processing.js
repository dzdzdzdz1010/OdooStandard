import { browser } from "@web/core/browser/browser";
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';

export class PaymentPostProcessing extends Interaction {
    static selector = 'div[name="o_payment_status"]';

    setup() {
        // Create a bus listener to trigger post processing
        const notificationType = 'PAYMENT_TRIGGER_POST_PROCESSING';
        const { notificationChannel, landingRoute } = this.el.dataset;
        this.busService = this.services.bus_service;
        this.busService.addChannel(notificationChannel);
        this.busService.subscribe(notificationType, this.triggerPostProcessing.bind(this));
        // Redirect automatically after 5 seconds
        this.waitForTimeout(() => {
            if (landingRoute) {
                window.location = landingRoute;
            }
        }, 5000);
        // Make sure bus listener is disposed properly when interaction is destroyed
        this.registerCleanup(() => {
            this.busService.unsubscribe(notificationType, this.triggerPostProcessing.bind(this));
            this.busService.deleteChannel(notificationChannel);
        });
    }

    async triggerPostProcessing() {
        const postProcessingData = await rpc('/payment/post_process', { csrf_token: odoo.csrf_token });
        const { provider_code, state, landing_route, status_message } = postProcessingData;
        if (['cancel', 'error'].includes(state)) {
            const defaultErrorMessage = "Payment was not successful, please try again.";
            browser.sessionStorage.setItem("errorMessage", status_message || defaultErrorMessage);
        }
        if (PaymentPostProcessing.getFinalStates(provider_code).has(state)) {
            window.location = landing_route;
        }
    }

    static getFinalStates(providerCode) {
        return new Set(['authorized', 'done', 'cancel', 'error']);
    }

}

registry
    .category('public.interactions')
    .add('payment.payment_post_processing', PaymentPostProcessing);
