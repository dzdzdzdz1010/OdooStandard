import { Plugin } from "@html_editor/plugin";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ProductTemplateOption } from "./product_template_option";

export class ProductTemplateOptionPlugin extends Plugin {
    static id = "productTemplateOptionPlugin";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, ProductTemplateOption),
        ],
        builder_actions: {},
        patch_builder_options: [
            {
                target_name: 'ProductsRibbonOption',
                target_element: 'selector',
                method: 'add',
                value: ProductTemplateOption.selector,
            },
        ],
    };
}

registry.category("website-plugins")
        .add(ProductTemplateOptionPlugin.id, ProductTemplateOptionPlugin);
