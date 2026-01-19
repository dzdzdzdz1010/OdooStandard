/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ListButtonCountWidget extends Component {
    static template = "hr.ListButtonCountWidget";
    static props = {
        ...standardFieldProps,
        icon: { type: String, optional: true },
        action: { type: String, optional: true },
    };

    get displayValue() {
        return this.props.record.data[this.props.name] || 0;
    }

    get icon() {
        return this.props.icon || '';
    }

    get action() {
        return this.props.action || '';
    }

    async onClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (!this.displayValue) {
            return;
        }
        if (this.props.action) {
            const action = await this.props.record.model.orm.call(
                this.props.record.resModel,
                this.props.action,
                [[this.props.record.resId]],
            );
            this.env.services.action.doAction(action);
        }
    }
}

export const listButtonCountField = {
    component: ListButtonCountWidget,
    supportedTypes: ["integer"],
    extractProps: ({ options }) => ({
        icon: options.icon,
        action: options.action,
    }),
};


registry.category("fields").add("list_button_count", listButtonCountField);
