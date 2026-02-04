import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import {
    ClickableBlockOption,
    ClickableCardParentOption,
    ClickableBlockquoteParentOption,
} from "./clickable_block_option";
import { unwrapContents } from "@html_editor/utils/dom";

export class ClickableBlockOptionPlugin extends Plugin {
    static id = "clickableBlockOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, ClickableBlockOption),
            withSequence(SNIPPET_SPECIFIC_END, ClickableCardParentOption),
            withSequence(SNIPPET_SPECIFIC_END, ClickableBlockquoteParentOption),
        ],
        builder_actions: {
            setBlockClickable,
            setBlockAnchorUrl,
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
        legit_empty_link_predicates: (linkEl) => linkEl.matches("a.stretched-link[href]"),
    };

    cleanForSave({ root }) {
        const stretchedLinkEls = root.querySelectorAll(".stretched-link");
        for (const linkEl of stretchedLinkEls) {
            linkEl.classList.remove("d-none");
        }
    }
}

class setBlockClickable extends BuilderAction {
    static id = "setBlockClickable";
    apply({ editingElement }) {
        // Remove all text links since they won't be clickable anymore.
        // Keep the buttons for cosmetic purpose
        const linkEls = editingElement.querySelectorAll("a:not(.btn)");
        for (const linkEl of linkEls) {
            unwrapContents(linkEl);
        }
        const anchorEl = document.createElement("a");
        anchorEl.classList.add("stretched-link", "position-static", "d-none");
        editingElement.prepend(anchorEl);
    }
    clean({ editingElement }) {
        editingElement.querySelector("a.stretched-link")?.remove();
    }
    isApplied({ editingElement }) {
        return !!editingElement.querySelector("a.stretched-link");
    }
}

class setBlockAnchorUrl extends BuilderAction {
    static id = "setBlockAnchorUrl";
    apply({ editingElement, value }) {
        if (value) {
            editingElement.querySelector("a.stretched-link").setAttribute("href", value);
        } else {
            editingElement.querySelector("a.stretched-link").removeAttribute("href");
        }
    }
    getValue({ editingElement }) {
        return editingElement.querySelector("a.stretched-link")?.getAttribute("href") || "";
    }
}

registry.category("website-plugins").add(ClickableBlockOptionPlugin.id, ClickableBlockOptionPlugin);
