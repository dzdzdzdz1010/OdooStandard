import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BuilderColorPicker } from "@html_builder/core/building_blocks/builder_colorpicker";
import { BuilderSelect } from "@html_builder/core/building_blocks/builder_select";
import { BuilderSelectItem } from "@html_builder/core/building_blocks/builder_select_item";
import { BuilderNumberInput } from "@html_builder/core/building_blocks/builder_number_input";
import { BuilderAction } from "@html_builder/core/builder_action";
import { StyleAction, withoutTransition } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

class LinkStyleOptionPlugin extends Plugin {
    static id = "linkStyleOption";
    resources = {
        builder_options: [LinkStyleOption],
        builder_actions: { LinkStyleAction, LinkFillColorAction },
    };
}

export class LinkStyleOption extends BaseOptionComponent {
    static template = "html_builder.LinkStyleOption";
    static selector = "a";
    static dependencies = ["linkStyle"];
    static components = {
        BuilderColorPicker,
        BuilderSelect,
        BuilderSelectItem,
        BuilderNumberInput,
        BorderConfigurator,
    };

    setup() {
        super.setup();

        const editingElement = this.env.getEditingElement();
        const computedStyle =
            editingElement.ownerDocument.defaultView.getComputedStyle(editingElement);
        this.state = useDomState((el) => ({
            type: this.dependencies.linkStyle.getType(el),
            textColor: computedStyle.color,
            fillColor: computedStyle.backgroundColor,
            border: computedStyle.border,
        }));
    }
}

class LinkStyleAction extends BuilderAction {
    static id = "linkStyleAction";
    static dependencies = ["linkStyle"];

    apply({ editingElement, params, value }) {
        const currentParam = params.mainParam;
        const linkStylePlugin = this.dependencies.linkStyle;

        const previousType = linkStylePlugin.getType(editingElement);
        if (currentParam === "type") {
            this.applyDefaultInlineStyle(editingElement, value, previousType);
        }

        editingElement.className = linkStylePlugin.computeClasses(editingElement, {
            type: currentParam === "type" ? value : previousType,
            size: currentParam === "size" ? value : linkStylePlugin.getSize(editingElement),
            shape: currentParam === "shape" ? value : linkStylePlugin.getShape(editingElement),
        });
    }

    applyDefaultInlineStyle(el, currentType, previousType) {
        const styleProps = ["color", "backgroundColor", "backgroundImage", "border"];
        if (currentType === "custom") {
            withoutTransition(el, () => {
                if (previousType === "link") {
                    el.classList.add("btn", "btn-primary");
                }
                const computedStyle = el.ownerDocument.defaultView.getComputedStyle(el);
                for (const prop of styleProps) {
                    if (computedStyle[prop] !== "none") {
                        el.style[prop] = computedStyle[prop];
                    }
                }
                if (computedStyle.borderStyle === "none") {
                    el.style.borderStyle = "solid";
                }
            });
        } else {
            for (const prop of styleProps) {
                el.style[prop] = "";
            }
        }
    }

    getValue({ editingElement, params }) {
        const currentParam = params.mainParam;
        const linkStylePlugin = this.dependencies.linkStyle;

        switch (currentParam) {
            case "type":
                return linkStylePlugin.getType(editingElement);
            case "size":
                return linkStylePlugin.getSize(editingElement);
            case "shape":
                return linkStylePlugin.getShape(editingElement);
        }
    }

    isApplied({ editingElement, params, value }) {
        return this.getValue({ editingElement, params }) === value;
    }
}

class LinkFillColorAction extends StyleAction {
    static id = "linkFillColorAction";
    static dependencies = ["color"];

    getValue(context) {
        // This override is needed because when the button is in outline mode,
        // the color is not shown unless we hover the button
        const { editingElement: el } = context;
        return el.style.backgroundColor || el.style.backgroundImage || super.getValue(context);
    }
}

registry.category("builder-plugins").add(LinkStyleOptionPlugin.id, LinkStyleOptionPlugin);
