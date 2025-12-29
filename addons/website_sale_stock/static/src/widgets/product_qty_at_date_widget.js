import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, onWillRender } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";

export class ProductQtyAtDatePopover extends Component {
    static template = "website_sale_stock.ProductQtyAtDatePopover";
    static props = {
        record: Object,
        calcData: Object,
        close: Function,
    };
    setup() {
        this.actionService = useService("action");
    }

    get availableLabel() {
        return _t("On Hand");
    }

    get forecastedLabel() {
        return _t("Forecasted");
    }

    async viewForecast() {
        const productId = this.props.record.resId;
        if (!productId) return;

        try {
            const action = await this.env.services.orm.call(
                "product.product",
                "action_product_forecast_report",
                [productId]
            );
            action.context = {
                ...action.context,
                active_id: productId,
                active_model: "product.product",
            };
            this.actionService.doAction(action);
            this.props.close();
        } catch (error) {
            console.error("Error opening forecast report:", error);
        }
    }
}

export class ProductQtyAtDateWidget extends Component {
    static components = { Popover: ProductQtyAtDatePopover };
    static template = "website_sale_stock.ProductQtyAtDate";
    static props = { ...standardWidgetProps };

    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.calcData = {};
        onWillRender(() => {
            this.initCalcData();
        });
    }

    initCalcData() {
        const { data } = this.props.record;

        this.calcData.forecasted_issue = "";
        this.calcData.qty_available = data.qty_available || 0;
        this.calcData.virtual_available = data.virtual_available || 0;

        if (this.calcData.qty_available <= 0) {
            this.calcData.forecasted_issue = "text-danger";
        } else if (this.calcData.virtual_available < 0) {
            this.calcData.forecasted_issue = "text-warning";
        }
    }

    async showPopup(ev) {
        const target = ev.currentTarget;
        this.popover.open(target, {
            record: this.props.record,
            calcData: this.calcData,
        });
    }
}

export const productQtyAtDateWidget = {
    component: ProductQtyAtDateWidget,
    fieldDependencies: [
        { name: "qty_available", type: "float" },
        { name: "virtual_available", type: "float" },
    ],
};

registry.category("view_widgets").add("product_qty_at_date_widget", productQtyAtDateWidget);
