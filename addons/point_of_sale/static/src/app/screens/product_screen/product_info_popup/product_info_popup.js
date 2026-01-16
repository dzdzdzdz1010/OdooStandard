/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * Props:
 *  {
 *      info: {object of data}
 *  }
 */
export class ProductInfoPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.ProductInfoPopup";
    static defaultProps = { confirmKey: false };

    setup() {
        super.setup();
        this.pos = usePos();
        Object.assign(this, this.props.info);
    }
    searchProduct(variant, attributeValue) {
        this.pos.setSelectedCategoryId(0);
        const attributeValueSearch = variant.values.length > 1 ? attributeValue.search : "";
        this.pos.searchProductWord = `${attributeValueSearch};product_tmpl_id:${this.props.product.product_tmpl_id}`;
        this.cancel();
    }
    _hasMarginsCostsAccessRights() {
        const isAccessibleToEveryUser = this.pos.config.is_margins_costs_accessible_to_every_user;
        const isCashierManager = this.pos.get_cashier().role === "manager";
        return isAccessibleToEveryUser || isCashierManager;
    }
}
