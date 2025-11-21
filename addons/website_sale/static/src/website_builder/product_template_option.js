import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ProductTemplateOption extends BaseOptionComponent {
    static template = "website_sale.ProductTemplateOption";
    static selector = ".o_wsale_product_page";
    static editableOnly = false;
    static title = _t("Product Template");

    setup() {
        this.orm = useService("orm");
        this.domState = useDomState(async (el) => {
            const productProduct = el.querySelector('[data-oe-model="product.product"]');
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const variantID = productProduct ? parseInt(productProduct.dataset.oeId) : null;
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
            const template = templateId ?
                    (await this.orm.searchRead(
                        "product.template",
                        [["id", "=", templateId]],
                        ["name", "product_tag_ids", "product_variant_ids"]
                    ))[0] : null;

            return {
                variantID,
                templateId,
                template,
            }
        })
    }
}
