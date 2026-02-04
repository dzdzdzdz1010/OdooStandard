import { BuilderInputSelectBase } from "@html_builder/core/building_blocks/builder_input_select_base";
import { BuilderTextInput } from "@html_builder/core/building_blocks/builder_text_input";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";

export class BuilderInputSelectText extends BuilderInputSelectBase {
    static template = "html_builder.BuilderInputSelectText";
    static components = { ...BuilderInputSelectBase.components, BuilderTextInput };
    static props = {
        ...BuilderTextInput.props,
        ...BuilderInputSelectBase.props,
    };

    get inputSelectTextProps() {
        return {
            ...pick(this.props, ...Object.keys(BuilderTextInput.props)),
            selectTextOnFocus: true,
        };
    }
}

class BuilderInputSelectTextPlugin extends Plugin {
    static id = "BuilderInputSelectTextPlugin";
    resources = {
        builder_components: {
            BuilderInputSelectText,
        },
    };
}

registry
    .category("builder-plugins")
    .add(BuilderInputSelectTextPlugin.id, BuilderInputSelectTextPlugin);
