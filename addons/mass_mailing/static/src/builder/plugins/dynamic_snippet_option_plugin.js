import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BEGIN } from "@html_builder/utils/option_sequence";

export class DynamicRecordPlugin extends Plugin {
    static id = "dynamicRecordOption";
    static shared = ["setRecord"];

    resources = {
        builder_options: [withSequence(BEGIN, DynamicRecordOption)],
        builder_actions: {
            SelectRecordAction,
        },
    };

    async setRecord(el, model, id, fragmentTemplate) {
        const fragmentContent = await this.services.orm.call(
            "mailing.mailing",
            "render_dynamic_template",
            [fragmentTemplate, model, id]
        );
        el.innerHTML = fragmentContent;
        el.dataset.model = model;
        el.dataset.id = id;
    }
}

export class DynamicRecordOption extends BaseOptionComponent {
    static template = "mass_mailing.dynamicRecordOption";
    static selector = ".s_dynamic_record";

    getElementDataModel() {
        return this.env.getEditingElement().dataset.model;
    }

    getElementFragmentId() {
        return this.env.getEditingElement().dataset.fragmentId;
    }
}

class SelectRecordAction extends BuilderAction {
    static dependencies = ["dynamicRecordOption"];
    static id = "selectRecordAction";
    setup() {
        this.utils = this.dependencies.dynamicRecordOption;
    }

    getValue({ editingElement: el }) {
        if (el.dataset.id) {
            return JSON.stringify({
                id: parseInt(el.dataset.id),
                display_name: el.dataset.displayName,
                name: el.dataset.name,
            });
        }
        return;
    }

    async apply({ editingElement: el, value, params }) {
        value = JSON.parse(value);
        await this.utils.setRecord(el, params.model, value.id, params.fragmentTemplate);
        el.dataset.name = value.name;
        el.dataset.displayName = value.display_name;
    }
}

registry.category("mass_mailing-plugins").add(DynamicRecordPlugin.id, DynamicRecordPlugin);
