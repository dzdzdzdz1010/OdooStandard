import { textInputBasePassthroughProps } from "@html_builder/core/building_blocks/builder_text_input_base";
import { BuilderUrlPicker } from "@html_builder/core/building_blocks/builder_urlpicker";
import { basicContainerBuilderComponentProps, useActionInfo } from "@html_builder/core/utils";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import wUtils from "@website/js/utils";

export class AutoCompleteInBuilderUrlPicker extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        inputClass: { type: String, optional: true },
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
    };
    static template = "website.AutoCompleteInBuilderUrlPicker";

    setup() {
        super.setup();
        this.info = useActionInfo();
    }

    get inputClass() {
        return this.props.inputClass;
    }

    get ulDropdownClass() {
        return `${super.ulDropdownClass} dropdown-menu ui-autocomplete o_website_ui_autocomplete`;
    }

    onInputChange(ev) {
        if (this.ignoreBlur) {
            ev.stopImmediatePropagation();
            return;
        }
        super.onInputChange(ev);
    }
}

patch(BuilderUrlPicker, {
    components: { ...BuilderUrlPicker.components, AutoCompleteInBuilderUrlPicker },
});

patch(BuilderUrlPicker.prototype, {
    setup() {
        super.setup();
        this.urlRef = useChildRef();
    },

    get sources() {
        const body = this.env.getEditingElement().ownerDocument.body;
        return [
            {
                placeholder: _t("Loading..."),
                options: (term) => wUtils.loadOptionsSource(term, body, this.onSelect.bind(this)),
                optionSlot: "urlOption",
            },
        ];
    },

    onSelect(value) {
        this.commit(value);
    },

    onChange(req) {
        this.commit(req.inputValue);
    },

    openPreviewUrl() {
        if (this.urlRef.el.value) {
            window.open(this.urlRef.el.value, "_blank");
        }
    },
});
