import { SelectionField, selectionField } from '@web/views/fields/selection/selection_field';
import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from '@web/core/registry';

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from '../../utils/project_utils';

export class ProjectColorStatusSelection extends SelectionField {
    static template = "project.ProjectColorStatusSelection";

    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || this.options[0][0];
    }

    statusColor(value) {
        return this.colors[value] ? this.colorPrefix + this.colors[value] : "";
    }
}

export const projectColorStatusSelection = {
    ...selectionField,
    component: ProjectColorStatusSelection,
};

export class ProjectColorStatus extends CharField {
    static template = "project.ProjectColorStatus";

    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || this.options[0][0];
    }

    statusColor(value) {
        return this.colors[value] ? this.colorPrefix + this.colors[value] : "";
    }
}

export const projectColorStatus = {
    ...charField,
    component: ProjectColorStatus,
};

registry.category("fields").add("color_status_selection", projectColorStatusSelection);
registry.category("fields").add("color_status", projectColorStatus);
