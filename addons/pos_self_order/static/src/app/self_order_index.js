<<<<<<< c2cd08ab199202ea592199a691baf97b50bd6d4c
import { Component } from "@odoo/owl";
||||||| 6058b071f31f04b3e6717b419b11661de7720a5b
import { Component, whenReady } from "@odoo/owl";
=======
import { mount, Component, reactive, whenReady } from "@odoo/owl";
>>>>>>> d465dd5bd36ff1418ff271e7b6e3f202ae9f22e7
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { Router } from "@pos_self_order/app/router";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { ComboPage } from "@pos_self_order/app/pages/combo_page/combo_page";
import { ProductPage } from "@pos_self_order/app/pages/product_page/product_page";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { EatingLocationPage } from "@pos_self_order/app/pages/eating_location_page/eating_location_page";
import { StandNumberPage } from "@pos_self_order/app/pages/stand_number_page/stand_number_page";
import { OrdersHistoryPage } from "@pos_self_order/app/pages/order_history_page/order_history_page";
import { LoadingOverlay } from "@pos_self_order/app/components/loading_overlay/loading_overlay";
import { hasTouch } from "@web/core/browser/feature_detection";
<<<<<<< c2cd08ab199202ea592199a691baf97b50bd6d4c
import { init as initDebugFormatters } from "@point_of_sale/app/utils/debug-formatter";
import { insertKioskStyle } from "./kiosk_style";
||||||| 6058b071f31f04b3e6717b419b11661de7720a5b
=======
import { Loader } from "@point_of_sale/app/components/loader/loader";
import { getTemplate } from "@web/core/templates";
>>>>>>> d465dd5bd36ff1418ff271e7b6e3f202ae9f22e7

export class selfOrderIndex extends Component {
    static template = "pos_self_order.selfOrderIndex";
    static props = [];
    static components = {
        Router,
        ProductPage,
        OrdersHistoryPage,
        ComboPage,
        PaymentPage,
        ConfirmationPage,
        ProductListPage,
        CartPage,
        EatingLocationPage,
        StandNumberPage,
        LandingPage,
        LoadingOverlay,
        MainComponentsContainer,
        Loader,
    };

    setup() {
        this.selfOrder = useSelfOrder();
        window.posmodel = this.selfOrder;

        // Disable cursor on touch devices (required on IoT Box Kiosk)
        if (hasTouch()) {
            document.body.classList.add("touch-device");
        }

        if (this.selfOrder.kioskMode) {
            document.documentElement.classList.add("kiosk");
        }

        const styleConfig = this.selfOrder.config._self_ordering_style;
        if (styleConfig) {
            const { primaryBgColor, primaryTextColor } = styleConfig;
            insertKioskStyle(primaryBgColor, primaryTextColor);
        }

        if (this.env.debug) {
            initDebugFormatters();
        }
    }
    get selfIsReady() {
        return this.selfOrder.models["product.product"].length > 0;
    }
}
<<<<<<< c2cd08ab199202ea592199a691baf97b50bd6d4c
||||||| 6058b071f31f04b3e6717b419b11661de7720a5b
whenReady(() => mountComponent(selfOrderIndex, document.body));
=======
whenReady(async () => {
    try {
        await mountComponent(selfOrderIndex, document.body);
    } catch (err) {
        const loader = reactive({ isShown: true, error: err });
        mount(Loader, document.body, {
            getTemplate,
            props: { loader },
            translatableAttributes: ["data-tooltip"],
            translateFn: (s) => s,
        });

        console.log(err);
    }
});
>>>>>>> d465dd5bd36ff1418ff271e7b6e3f202ae9f22e7
