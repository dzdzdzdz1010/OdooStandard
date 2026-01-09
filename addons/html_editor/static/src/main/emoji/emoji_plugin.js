import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";
import { EmojiListPicker } from "./emoji_list_picker";
import { debounce } from "@bus/workers/bus_worker_utils";

/**
 * @typedef { Object } EmojiShared
 * @property { EmojiPlugin['showEmojiPicker'] } showEmojiPicker
 */

export class EmojiPlugin extends Plugin {
    static id = "emoji";
    static dependencies = ["history", "overlay", "dom", "selection", "delete"];
    static shared = ["showEmojiPicker"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "addEmoji",
                title: _t("Emoji"),
                description: _t("Add an emoji"),
                icon: "fa-smile-o",
                run: this.showEmojiPicker.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "widget",
                commandId: "addEmoji",
            },
        ],

        input_handlers: this.onInput.bind(this),
        delete_handlers: () => this.updateEmojiList(),
        post_undo_handlers: () => this.updateEmojiList(),
        post_redo_handlers: () => this.updateEmojiList(),
    };

    setup() {
        this.overlay = this.dependencies.overlay.createOverlay(EmojiPicker, {
            hasAutofocus: true,
            className: "popover",
        });
        this.emojiListOverlay = this.dependencies.overlay.createOverlay(EmojiListPicker, {
            className: "popover",
        });
        this.emojiListState = reactive({});
        this.addDomListener(this.document, "keydown", this.onKeyDown);
    }

    onInput(ev) {
        if (ev.data === ":") {
            this.emojiListOverlay.close();
            const selection = this.dependencies.selection.getEditableSelection();
            this.offset = selection.startOffset - 1;
            this.shouldUpdateEmojiList = true;
        } else {
            this.updateEmojiList();
        }
    }

    onKeyDown(ev) {
        if (ev.key === "Escape") {
            this.emojiListOverlay.close();
            this.shouldUpdateEmojiList = false;
        }
    }

    /**
     * @param {Object} options
     * @param {HTMLElement} options.target - The target element to position the overlay.
     * @param {Function} [options.onSelect] - The callback function to handle the selection of an emoji.
     * If not provided, the emoji will be inserted into the editor and a step will be trigerred.
     */
    showEmojiPicker({ target, onSelect } = {}) {
        this.overlay.open({
            props: {
                close: () => {
                    this.overlay.close();
                    this.dependencies.selection.focusEditable();
                },
                onSelect: (str) => {
                    if (onSelect) {
                        onSelect(str);
                        return;
                    }
                    this.dependencies.dom.insert(str);
                    this.dependencies.history.addStep();
                },
            },
            target,
        });
    }

    updateEmojiList = debounce(this._updateEmojiList, 100);
    _updateEmojiList() {
        if (!this.shouldUpdateEmojiList) {
            return;
        }

        const selection = this.dependencies.selection.getEditableSelection();
        this.searchNode = selection.startContainer;
        if (!this.isSearching(selection)) {
            this.emojiListOverlay.close();
            this.shouldUpdateEmojiList = false;
            return;
        }

        const searchTerm = this.searchNode.nodeValue.slice(this.offset, selection.endOffset);
        this.emojiListState.searchTerm = searchTerm;
        if (searchTerm.length > 2) {
            this.emojiListOverlay.open({
                props: {
                    state: this.emojiListState,
                    onSelect: (str) => {
                        const selection = this.document.getSelection();
                        selection.extend(this.searchNode, this.offset);
                        this.dependencies.delete.deleteSelection();
                        this.dependencies.dom.insert(str);
                        this.dependencies.history.addStep();
                        this.emojiListOverlay.close();
                    },
                    close: () => {
                        this.emojiListOverlay.close();
                        this.dependencies.selection.focusEditable();
                    },
                    overlay: this.emojiListOverlay,
                },
            });
        } else {
            this.emojiListOverlay.close();
        }
    }

    isSearching(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue &&
            this.searchNode.nodeValue[this.offset] === ":" &&
            selection.endOffset > this.offset
        );
    }
}
