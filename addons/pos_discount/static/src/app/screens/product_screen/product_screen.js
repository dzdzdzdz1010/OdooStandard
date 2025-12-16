import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        if (!this.currentOrder?.getSelectedOrderline()?.isDiscountLine) {
            return buttons;
        }
        const toDisable = new Set(["quantity", "discount"]);
        return buttons.map((button) => {
            if (toDisable.has(button.value)) {
                return { ...button, disabled: true };
            }
            return button;
        });
    },
<<<<<<< 2e38766eb0e4606f475c6976746255fb40921787
    async addProductToOrder(product) {
        await super.addProductToOrder(product);
        const discountLine = this.currentOrder.getDiscountLine();
        if (discountLine) {
            const value = discountLine.extra_tax_data?.discount_value;
            const type = discountLine.extra_tax_data?.discount_type;
            if (value) {
                const selectLine = this.currentOrder?.getSelectedOrderline();
                await this.pos.applyDiscount(value, type, this.currentOrder);
                this.pos.selectOrderLine(this.currentOrder, selectLine);
            } else {
                discountLine.delete();
            }
        }
    },
||||||| bf7dee8069f203095c44381708153865d3e8f19e
    async addProductToOrder(product) {
        await super.addProductToOrder(product);
        const discountLine = this.currentOrder.getDiscountLine();
        if (discountLine) {
            const percentage = discountLine.extra_tax_data?.discount_percentage;
            if (percentage) {
                const selectLine = this.currentOrder?.getSelectedOrderline();
                await this.pos.applyDiscount(percentage, this.currentOrder);
                this.pos.selectOrderLine(this.currentOrder, selectLine);
            } else {
                discountLine.delete();
            }
        }
    },
=======
>>>>>>> 856b2f49794b46df507c4f0d4876e9d8bf2aeade
});
