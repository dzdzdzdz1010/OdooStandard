import {
    BaseOptionComponent,
    useDomState,
    SPECIAL_BLOCKQUOTE_SELECTOR,
    BLOCKQUOTE_PARENT_HANDLERS,
} from "@html_builder/core/utils";
import { SPECIAL_CARD_SELECTOR, CARD_PARENT_HANDLERS } from "./utils";

export class ClickableBlockOption extends BaseOptionComponent {
    static template = "website.ClickableBlockOption";
    static selector = `.carousel .carousel-item, .s_card, .s_blockquote`;
    static exclude = `.s_image_gallery .carousel-item, ${SPECIAL_CARD_SELECTOR}, ${SPECIAL_BLOCKQUOTE_SELECTOR}`;

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasHref: editingElement.querySelector("a.stretched-link")?.hasAttribute("href"),
        }));
    }
}

export class ClickableCardParentOption extends ClickableBlockOption {
    static selector = CARD_PARENT_HANDLERS;
    static exclude = "";
    static applyTo = ".s_card";
}

export class ClickableBlockquoteParentOption extends ClickableBlockOption {
    static selector = BLOCKQUOTE_PARENT_HANDLERS;
    static exclude = "";
    static applyTo = ".s_blockquote";
}
