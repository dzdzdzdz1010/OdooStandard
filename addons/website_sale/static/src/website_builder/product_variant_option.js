import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ProductVariantOption extends BaseOptionComponent {
    static template = "website_sale.ProductVariantOption";
    static selector = "#product_detail";
    static editableOnly = false;
    static title = _t("Product Variant");

    setup() {
        this.orm = useService("orm");
        this.domState = useDomState(async (el) => {
            const productProduct = el.querySelector('[data-oe-model="product.product"]');
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const variantId = productProduct ? parseInt(productProduct.dataset.oeId) : null;
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;

            return {
                variantId,
                templateId,
            }
        })
    }
}
