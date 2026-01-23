import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { useNavigation } from "@web/core/navigation/navigation";
import { fuzzyLookup } from "@web/core/utils/search";

export class EmojiListPicker extends Component {
    static props = {
        state: Object,
        onSelect: Function,
        close: Function,
        overlay: Object,
    };
    static template = "html_editor.EmojiListPicker";

    setup() {
        this.emojiListPicker = useRef("emojiListPicker");
        this.state = useState({
            emojis: [],
        });
        this.allEmojis = [];

        this.navigation = useNavigation(this.emojiListPicker, {
            isNavigationAvailable: () => this.props.overlay.isOpen,
            shouldFocusFirstItem: true,
            hotkeys: {
                "shift+Enter": {
                    bypassEditableProtection: true,
                    isAvailable: () => true,
                    callback: (navigator) => {
                        navigator.activeItem.select();
                    },
                },
            },
        });

        onWillStart(async () => {
            const { emojis } = await loadEmoji();
            this.allEmojis = emojis;
            this.updateResults();
        });

        useEffect(
            () => {
                this.updateResults();
            },
            () => [this.props.state.searchTerm]
        );
    }

    updateResults() {
        const emojis = fuzzyLookup(this.props.state.searchTerm || "", this.allEmojis, (e) => [
            e.name,
            ...e.shortcodes,
            ...e.keywords,
        ]).slice(0, 8);

        if (emojis.length > 0) {
            this.state.emojis = emojis;
        } else {
            this.props.close();
        }
    }

    onClick(emoji) {
        this.props.onSelect(emoji.codepoints);
    }
}
