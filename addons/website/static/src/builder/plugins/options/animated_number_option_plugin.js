import { before, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AnimatedNumberOption } from "./animated_number_option";
import { BuilderAction } from "@html_builder/core/builder_action";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "AnimatedNumberOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(before(SNIPPET_SPECIFIC_END), AnimatedNumberOption)],
        so_content_addition_selector: [".s_animated_number"],
        builder_actions: {
            ToggleTitleAnimatedNumberAction,
        },
    };
}

export class ToggleTitleAnimatedNumberAction extends BuilderAction {
    static id = "toggleTitleAnimatedNumber";

    isApplied({ editingElement }) {
        return !!editingElement.querySelector(".s_animated_number_label");
    }
    apply({ editingElement }) {
        const titleEl = document.createElement("div");
        titleEl.classList.add(
            "s_animated_number_label",
            "d-flex",
            "justify-content-center",
            "align-items-center"
        );
        const h2El = document.createElement("h2");
        h2El.textContent = "Clients";
        titleEl.append(h2El);
        editingElement.prepend(titleEl);
    }
    clean({ editingElement }) {
        editingElement.querySelector(".s_animated_number_label").remove();
    }
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);
