/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";
import { View } from "@web/views/view";

import "@resource/views/calendar/resource_calendar_view";

export class CalendarOne2Many extends Component {
    static template = "resource.CalendarOne2Many";
    static components = { View };
    static props = {
        ...standardFieldProps,
    };

    get viewProps() {
        return {
            type: "calendar",
            resModel: this.props.record.data[this.props.name].resModel,
            domain: [["calendar_id", "=", this.props.record.resId]],
            display: { controlPanel: false },
            searchViewId: false,
            className: "h-100 w-100 d-flex",
            context: {
                ...this.props.context,
                default_calendar_id: this.props.record.resId,
            },
        };
    }
}

export const calendarOne2Many = {
    component: CalendarOne2Many,
    displayName: _t("Relational table"),
    supportedTypes: ["one2many", "many2many"],
    useSubView: true,
    extractProps: ({ attrs, relatedFields, viewMode, views, widget, string }, dynamicInfo) => {
        const props = {
            addLabel: attrs["add-label"],
            context: dynamicInfo.context,
            domain: dynamicInfo.domain,
            crudOptions: pick(attrs, "create", "delete", "link", "unlink", "write"),
            string,
        };
        if (viewMode) {
            props.views = views;
            props.viewMode = viewMode;
            props.relatedFields = relatedFields;
        }
        if (widget) {
            props.widget = widget;
        }
        return props;
    },
};

registry.category("fields").add("calendar_one2many", calendarOne2Many);
