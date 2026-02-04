import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    get lineScreenValues() {
        const line_screen_values = super.lineScreenValues;
        return {
            ...line_screen_values,
            lotLines: this.line.product_id?.tracking !== "none" && (this.line?.packLotLines || []),
        };
    },
});
