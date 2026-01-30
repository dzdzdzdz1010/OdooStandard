import { formatFloatTime } from "@web/views/fields/formatters";
import { Record } from "@web/model/record";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Component, useRef, useState } from "@odoo/owl";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

export class ResourcePopover extends Component {
    static template = "resource.ResourcePopover";
    static components = {
        Record,
        FormRenderer,
        ViewButton,
    };
    static props = {
        close: Function,
        readonly: { type: Boolean },
        onReload: Function,
        originalRecord: { type: Object },
        recordProps: { type: Object },
        archInfo: { type: Object },
        getSource: Function,
        getDurationStr: Function,
        isSplittable: { type: Boolean, optional: true },
    };
    static defaultProps = {
        isSplittable: false,
    }

    setup() {
        this.state = useState({
            isSplit: false,
            originalDuration: this.props.originalRecord?.duration,
            newRecordValues: {
                hour_from: 0,
                hour_to: 0,
                duration: 0,
            },
        });
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
            ...(!this.props.originalRecord?.id ? { values: this.props.originalRecord } : {}),
            mode: this.props.readonly ? "readonly" : "edit",
            hooks: {
                onRecordChanged: (record, changes) => {
                    if (changes.duration) {
                        this.state.newRecordValues = {
                            ...this.state.newRecordValues,
                            duration: Math.max(
                                0,
                                this.state.originalDuration - record.data.duration
                            ),
                        };
                    }
                },
            },
        };
    }

    newRecordProps(currentRecord) {
        return {
            ...this.props.recordProps,
            mode: "edit",
            values: {
                ...currentRecord?.data,
                ...this.state.newRecordValues,
                ...(currentRecord?.data.date ? {date: serializeDate(currentRecord.data.date)} : {}),
            },
            hooks: {
                onRecordChanged: (record, changes) => {
                    this.state.newRecordValues = record.data;
                },
            },
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

    onToggleSplit() {
        this.state.isSplit = !this.state.isSplit;
    }

    async onSave(currentRecord, newRecord) {
        await executeButtonCallback(this.rootRef.el, async () => {
            const areValid =
                (await currentRecord.checkValidity()) &&
                (!this.state.isSplit || (await newRecord.checkValidity()));
            if (areValid) {
                if (this.state.isSplit) {
                    await newRecord.save();
                }
                await currentRecord.save();
                await this.props.onReload();
                this.props.close();
            }
        });
    }
}
