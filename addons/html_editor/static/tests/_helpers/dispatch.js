import { removeClass } from "@html_editor/utils/dom";

function trigger(editor, resourceId, ...args) {
    (editor.resources[resourceId] || []).forEach((fn) => fn(...args));
}

export function triggerNormalize(editor) {
    trigger(editor, "normalize_listeners", editor.editable);
}

export function cleanHints(editor) {
    for (const element of editor.editable.querySelectorAll(".o-we-hint")) {
        removeClass(element, "o-we-hint");
        element.removeAttribute("o-we-hint-text");
    }
}

export function triggerCleanForSave(editor, payload) {
    trigger(editor, "clean_for_save_listeners", payload);
}
