import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class UnsubscribeOptionPlugin extends Plugin {
    static id = "unsubscribeOptionPlugin";
    static dependencies = [];
    resources = {
        dropzone_selector: {
            selector: ".s_unsubscribe_link",
            dropNear: "p, h1, h2, h3, blockquote, .s_hr",
        },
    };
}

registry.category("mass_mailing-plugins").add(UnsubscribeOptionPlugin.id, UnsubscribeOptionPlugin);
