import { formatFloatTime } from "@web/views/fields/formatters";
import { Record } from "@web/model/record";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Component, useRef, useState } from "@odoo/owl";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

export class ResourcePopover extends Component {
    static template = "resource.ResourcePopover";
    static components = {
        Record,
        FormRenderer,
        ViewButton,
    };
    static props = {
        close: Function,
        onReload: Function,
        originalRecord: { type: Object },
        recordProps: { type: Object },
        archInfo: { type: Object },
        getSource: Function,
        getDurationStr: Function,
        context: { type: Object },
    };

    setup() {
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        useViewButtons(this.rootRef, {
            reload: this.props.onReload,
            afterExecuteAction: this.props.close,
        });
    }

    get currentRecordProps() {
        return {
            ...this.props.recordProps,
            resId: this.props.originalRecord?.id,
            mode: "edit",
            context: this.props.context,
        };
    }

    get archInfo() {
        return this.props.archInfo;
    }

    getTitle(record) {
        if (!record.data) {
            return null;
        }
        if (record.data.duration_based && record.data.duration_hours) {
            return _t("%(duration)s Attendance", {
                duration: formatFloatTime(record.data.duration_hours, {
                    noLeadingZeroHour: true,
                }),
            });
        } else if (record.data.hour_from || record.data.hour_to) {
            return _t("%(hour_from)s - %(hour_to)s Attendance", {
                hour_from: formatFloatTime(record.data.hour_from, {
                    noLeadingZeroHour: true,
                }),
                hour_to: formatFloatTime(record.data.hour_to, {
                    noLeadingZeroHour: true,
                }),
            });
        }
        return null;
    }

    getDurationStr(duration) {
        const durationStr = formatFloatTime(duration, {
            noLeadingZeroHour: true,
        }).replace(/(:00|:)/g, "h");
        return ` ${durationStr}`;
    }

    async onSave(currentRecord) {
        await executeButtonCallback(this.rootRef.el, async () => {
            if (await currentRecord.checkValidity()) {
                try {
                    await currentRecord.save();
                    await this.props.onReload();
                    this.props.close();
                } catch (error) {
                    return this.notification.add(_t(error.data.message), { type: "danger" });
                }
            }
        });
    }
}
