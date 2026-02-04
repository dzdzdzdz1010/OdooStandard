import { BuilderInputSelectBase } from "@html_builder/core/building_blocks/builder_input_select_base";
import { BuilderNumberInput } from "@html_builder/core/building_blocks/builder_number_input";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";

export class BuilderInputSelectNumber extends BuilderInputSelectBase {
    static template = "html_builder.BuilderInputSelectNumber";
    static components = { ...BuilderInputSelectBase.components, BuilderNumberInput };
    static props = {
        ...BuilderNumberInput.props,
        ...BuilderInputSelectBase.props,
    };

    get inputSelectNumberProps() {
        return {
            ...pick(this.props, ...Object.keys(BuilderNumberInput.props)),
            selectTextOnFocus: true,
        };
    }
}

class BuilderInputSelectNumberPlugin extends Plugin {
    static id = "BuilderInputSelectNumberPlugin";
    resources = {
        builder_components: {
            BuilderInputSelectNumber,
        },
    };
}

registry
    .category("builder-plugins")
    .add(BuilderInputSelectNumberPlugin.id, BuilderInputSelectNumberPlugin);
