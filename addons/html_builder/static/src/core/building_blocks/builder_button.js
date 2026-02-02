import { Component } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useLanguageDirection,
    useSelectableItemComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { Image } from "../img";
import { _t } from "@web/core/l10n/translation";

export class BuilderButton extends Component {
    static template = "html_builder.BuilderButton";
    static components = { BuilderComponent, Image };
    static props = {
        ...clickableBuilderComponentProps,

        title: { type: String, optional: true },
        titleActive: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        iconImgAttrs: { type: Object, optional: true },
        icon: { type: String, optional: true },
        className: { type: String, optional: true },
        classActive: { type: String, optional: true },
        style: { type: String, optional: true },
        type: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        type: "secondary",
        titleActive: "",
        iconImgAttrs: {},
    };

    setup() {
        this.info = useActionInfo();
        const { state, operation } = useSelectableItemComponent(this.props.id);
        this.state = state;
        this.onClick = operation.commit;
        this.onPointerEnter = operation.preview;
        this.onPointerLeave = operation.revert;
    }

    get className() {
        let className = this.props.className || "";
        if (this.props.type) {
            className += ` btn-${this.props.type}`;
        }
        if (this.state.isActive) {
            className = `active ${className}`;
            if (this.props.classActive) {
                className += ` ${this.props.classActive}`;
            }
        }
        if (this.props.icon) {
            className += ` o-hb-btn-has-icon`;
        }
        if (this.props.iconImg) {
            className += ` o-hb-btn-has-img-icon`;
        }
        return className;
    }

    get iconClassName() {
        if (this.props.icon.startsWith("fa-")) {
            return `fa ${this.props.icon}`;
        } else if (this.props.icon.startsWith("oi-")) {
            return `oi ${this.props.icon}`;
        }
        return "";
    }
}

const ltrRtlSplittableProps = [
    "className",
    "actionParam",
    "actionValue",
    "classAction",
    "styleAction",
    "styleActionValue",
    "attributeAction",
    "attributeActionValue",
    "dataAttributeAction",
];

/**
 * Many options are BuilderButtonGroups with at least a "Left" and a "Right"
 * button, but their action actually depends on the start and end of the line
 * (e.g. `flex-row` vs `flex-row-reverse`). They need some logic to work across
 * all 4 possible combinations of LTR / RTL in the backend (builder) and the
 * frontend (iframe).
 * The `BuilderButtonLtrRtl` is a helper component to share the logic.
 *
 * All the "ltrRtlSplittableProps" can either take a single value if it applies
 * to both, or a "primary" key (when the backend and frontend directions are the
 * same) and a "secondary" key (when they are different).
 */
export class BuilderButtonLtrRtl extends Component {
    static template = "html_builder.BuilderButtonLtrRtl";
    static components = { BuilderButton };
    static props = {
        position: { validate: (v) => ["start", "end"].includes(v) },
        label: { type: Object, optional: true },
        title: { type: String, optional: true },
        id: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        icon: { type: String, optional: true },
        className: { type: Object, optional: true },
        actionParam: { type: Object, optional: true },
        actionValue: { type: Object, optional: true },
        classAction: { type: Object, optional: true },
        styleAction: { type: Object, optional: true },
        styleActionValue: { type: Object, optional: true },
        attributeAction: { type: Object, optional: true },
        attributeActionValue: { type: Object, optional: true },
        dataAttributeAction: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        label: { left: _t("Left"), right: _t("Right") },
        className: { primary: undefined, secondary: undefined },
        actionParam: { primary: undefined, secondary: undefined },
        actionValue: { primary: undefined, secondary: undefined },
        classAction: { primary: undefined, secondary: undefined },
        styleAction: { primary: undefined, secondary: undefined },
        styleActionValue: { primary: undefined, secondary: undefined },
        attributeAction: { primary: undefined, secondary: undefined },
        attributeActionValue: { primary: undefined, secondary: undefined },
        dataAttributeAction: { primary: undefined, secondary: undefined },
    };

    setup() {
        this.langDir = useLanguageDirection();
        this.iconImgAttrs =
            this.langDir.backend === "ltr" ? {} : { style: "transform: scaleX(-1);" };

        for (const prop of ltrRtlSplittableProps) {
            if (
                this.props[prop] instanceof Object &&
                "primary" in this.props[prop] &&
                "secondary" in this.props[prop]
            ) {
                this[prop] = this.props[prop];
            } else {
                this[prop] = { primary: this.props[prop], secondary: this.props[prop] };
            }
        }
    }

    get title() {
        if ((this.langDir.backend === "ltr") === (this.props.position === "start")) {
            return this.props.label.left;
        }
        return this.props.label.right;
    }
}
