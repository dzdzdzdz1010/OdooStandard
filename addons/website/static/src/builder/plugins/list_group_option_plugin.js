import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { fonts } from "@html_editor/utils/fonts";

export class ListGroupOption extends BaseOptionComponent {
    static template = "website.ListGroupOption";
    static selector = ".s_list_group";
}

class ListGroupOptionPlugin extends Plugin {
    static id = "listGroupOptionPlugin";
    resources = {
        builder_options: [ListGroupOption],
        so_content_addition_selector: [".s_list_group"],
        builder_actions: {
            ReplaceListIconAction,
        },
    };
}

export class ReplaceListIconAction extends BuilderAction {
    static id = "replaceListIcon";
    static dependencies = ["media"];
    async load() {
        return new Promise((resolve) => {
            const mediaDialogParams = {
                visibleTabs: ["ICONS"],
                save: (icon) => {
                    resolve(icon);
                },
            };
            const onClose = this.dependencies.media.openMediaDialog(mediaDialogParams);
            onClose.then(resolve);
        });
    }
    apply({ editingElement, loadResult: savedIconEl }) {
        if (!savedIconEl) {
            return;
        }
        fonts.computeFonts();
        const data = fonts.fontIcons[0].cssData.find((rule) =>
            rule.names.includes(savedIconEl.classList[1])
        );
        const iconUnicode = data.css.match(/content:\s*["'](.*?)["']/)[1];
        editingElement.style.setProperty("--s_list_group-icon-content", `"${iconUnicode}"`);
    }
}

registry.category("website-plugins").add(ListGroupOptionPlugin.id, ListGroupOptionPlugin);
