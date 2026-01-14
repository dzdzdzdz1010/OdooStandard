import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";
import { ConnectionLostError } from "@web/core/network/rpc";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { hasTouch } from "@web/core/browser/feature_detection";

export class BadgeSelectionField extends Component {
    static template = "web.BadgeSelectionField";
    static props = {
        ...standardFieldProps,
        domain: { type: [Array, Function], optional: true },
        size: {
            type: String,
            optional: true,
            validate: (s) => ["sm", "md", "lg"].includes(s),
            default: "md",
        },
        badgeLimit: {
            type: Number,
            optional: true,
            default: 0,
        },
        placeholder: { type: String, optional: true },
        // Icon Props
        defaultIcon: { type: String, optional: true },
        // --- Many2one ---
        relatedIconField: { type: String, optional: true },
        // --- Selection ---
        // Static mapping from XML options: { 'selection_key': 'fa-icon' }
        iconMapping: { type: Object, optional: true },
        // Field name used to filter the visible selection options
        allowedSelectionField: { type: String, optional: true },
    };
    static defaultProps = {
        defaultIcon: "fa-check",
        iconMapping: {},
    };
    static components = {
        SelectMenu,
    };

    setup() {
        const { record, name, domain: propDomain, relatedIconField, defaultIcon } = this.props;
        const field = record.fields[name];
        this.type = field.type;

        if (this.type !== "many2one") {
            return;
        }

        this.specialData = useSpecialData(async (orm) => {
            const domain = getFieldDomain(record, name, propDomain);
            const { relation } = field;

            try {
                if (relatedIconField) {
                    const records = await orm.call(relation, "search_read", [], {
                        domain,
                        fields: ["display_name", relatedIconField],
                    });

                    return records.map((r) => [
                        r.id,
                        r.display_name,
                        r[relatedIconField] || defaultIcon,
                    ]);
                }

                return await orm.call(relation, "name_search", ["", domain]);
            } catch (error) {
                if (error instanceof ConnectionLostError) {
                    const currentVal = record.data[name];

                    if (!currentVal) {
                        return [];
                    }

                    return [[currentVal.id, currentVal.display_name, defaultIcon]];
                }
                throw error;
            }
        });
    }

    get options() {
        const options = this._getBaseOptions();

        // Map the corresponding icon to each option
        return options.map(([value, label, icon]) => {
            const finalIcon = this.type === "selection" ? this._getSelectionIcon(value) : icon;
            return [value, label, finalIcon];
        });
    }

    get string() {
        switch (this.type) {
            case "many2one":
                return this.props.record.data[this.props.name]
                    ? this.props.record.data[this.props.name].display_name
                    : "";
            case "selection":
                return this.props.record.data[this.props.name] !== false
                    ? this.options.find((o) => o[0] === this.props.record.data[this.props.name])[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return this.type === "many2one" && rawValue ? rawValue.id : rawValue;
    }

    get hasMoreThanMax() {
        return this.props.badgeLimit && this.options.length > this.props.badgeLimit;
    }

    get selectOptions() {
        return this.options.map(([value, label]) => ({ value, label }));
    }

    get isBottomSheet() {
        return this.env.isSmall && hasTouch();
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {string | number | false} value
     */
    onChange(value) {
        switch (this.type) {
            case "many2one":
                if (!value) {
                    this.props.record.update({ [this.props.name]: false });
                } else {
                    const option = this.options.find((option) => option[0] === value);
                    this.props.record.update({
                        [this.props.name]: { id: option[0], display_name: option[1] },
                    });
                }
                break;
            case "selection":
                if (value === this.value) {
                    const { required } = this.props.record.fields[this.props.name];
                    if (!required) {
                        this.props.record.update({ [this.props.name]: false });
                    }
                } else {
                    this.props.record.update({ [this.props.name]: value });
                }
                break;
        }
    }

    /**
     * Retrieves the base options without icons.
     * @returns {Array}.
     */
    _getBaseOptions() {
        const props = this.props;
        const record = props.record;
        let options = [];

        if (this.type === "many2one" && this.specialData.data) {
            options = this.specialData.data;
        }

        if (this.type === "selection") {
            options = record.fields[props.name].selection;
            if (props.allowedSelectionField) {
                const allowedOptions = record.data[props.allowedSelectionField];

                // Ensure an array or a JSON array is passed as the allowedSelectionField
                // Otherwise return all the options without filtering
                if (
                    !allowedOptions ||
                    (!Array.isArray(allowedOptions) && typeof allowedOptions !== "string")
                ) {
                    return options;
                }

                options = options.filter(([value]) => allowedOptions.includes(value));
            }
        }

        return options;
    }

    /**
     * Maps a specific option's value to its corresponding icon.
     * Returns defaultIcon(fa-check) if no icon corresponds to the value.
     * @param {string|number} value
     * @returns {string}
     */
    _getSelectionIcon(value) {
        const iconMapping = this.props.iconMapping;
        return iconMapping[value] || this.props.defaultIcon;
    }
}

export const badgeSelectionField = {
    component: BadgeSelectionField,
    displayName: _t("Badges"),
    supportedTypes: ["many2one", "selection"],
    supportedOptions: [
        {
            label: _t("Size"),
            name: "size",
            type: "selection",
            choices: [
                { label: _t("Small"), value: "sm" },
                { label: _t("Medium"), value: "md" },
                { label: _t("Large"), value: "lg" },
            ],
            default: "md",
        },
        {
            label: _t("Maximum Visible Badges"),
            name: "badgeLimit",
            type: "number",
            default: 0,
            placeholder: _t("Unlimited"),
            help: _t("Displays a dropdown if the badge count is higher than this value."),
        },
    ],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ options, placeholder }, dynamicInfo) => ({
        placeholder,
        domain: dynamicInfo.domain,
        size: options.size,
        badgeLimit: options.badgeLimit,
        relatedIconField: options.related_icon_field,
        iconMapping: options.icon_mapping,
        allowedSelectionField: options.allowed_selection_field,
        defaultIcon: options.default_icon,
    }),
};

registry.category("fields").add("selection_badge", badgeSelectionField);
