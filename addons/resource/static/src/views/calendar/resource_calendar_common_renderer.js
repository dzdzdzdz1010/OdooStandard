import { convertRecordToEvent } from "@web/views/calendar/utils";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";
import { ResourcePopover } from "../../components/resource_popover/resource_popover";
import {serializeDate, serializeDateTime} from "@web/core/l10n/dates";
import {usePopover} from "@web/core/popover/popover_hook";

export class ResourceCalendarCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer,
    };

    setup() {
        super.setup();
        this.popover = usePopover(ResourcePopover, {
            position: "right",
            onClose: () => {
                this.fc.api.unselect();
            },
        });
        this.resourcePopoverService = useService("resourcePopoverService");
        this.resourcePopoverService.setup(this.props.model.meta, this.additionalFieldsToFetch);
    }

    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            selectable: this.props.model.canCreate,
            forceEventDuration: true,
        };
    }

    handleDateClick(info) {
        if (!info.jsEvent || info.jsEvent.defaultPrevented) {
            // The event might be fired after a touch pointerup without any jsEvent
            return;
        }
        this.onDateClick(info);
    }

    onEventDragStart(info) {
        if (info.event.allDay) {
            const hours = Math.floor(info.event.extendedProps.forcedDuration);
            const minutes = Math.round((info.event.extendedProps.forcedDuration - hours) * 60);
            info.view.calendar.setOption(
                "defaultTimedEventDuration",
                `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`
            );
        }
        super.onEventDragStart(...arguments);
    }

    onEventDrop(info) {
        if (info.oldEvent.allDay) {
            info.view.calendar.setOption("defaultTimedEventDuration", "01:00");
        }
        super.onEventDrop(...arguments);
    }

    get additionalFieldsToFetch() {
        return [
            { name: "calendar_id", type: "many2one", readonly: false },
            { name: "date", type: "date", readonly: false },
            { name: "duration_based", type: "boolean", readonly: false },
        ];
    }

    async onSelect(info) {
        info.jsEvent?.preventDefault();
        const start = luxon.DateTime.fromJSDate(info.start)
        const end = luxon.DateTime.fromJSDate(info.end)
        this.popover.open(
            info.jsEvent?.toElement ?? info.view.calendar.el.querySelector(".fc-event-mirror"),
            {
                ...this.getPopoverProps(null),
                context: {
                    ...this.props.model.meta.context,
                    default_date: serializeDate(start),
                    default_hour_from: start.hour+start.minute/60,
                    default_hour_to: end.hour+end.minute/60,
                },
                onClose: () => this.fc.api.unselect()
            },
            `o_cw_popover card o_calendar_color_0`
        );
    }

    onDateClick(info) {
        const date = luxon.DateTime.fromJSDate(info.date)
        info.view.calendar.select(date.toISO(), date.plus({hours: 1}).toISO())
    }

    convertRecordToEvent(record) {
        const res = super.convertRecordToEvent(...arguments);
        res.forcedDuration = record.duration;
        return res;
    }

    fcEventToRecord(event) {
        const { id, allDay, date, start, end } = event;
        const res = {
            start: luxon.DateTime.fromJSDate(date || start),
            isAllDay: allDay,
        };
        if (end) {
            res.end = luxon.DateTime.fromJSDate(end);
            if (allDay) {
                res.end = res.end.minus({ days: 1 });
            }
        }
        if (id) {
            const existingRecord = this.props.model.records[id];
            if (this.props.model.scale === "month") {
                res.start = res.start?.set({
                    hour: existingRecord.start.hour,
                    minute: existingRecord.start.minute,
                });
                if (existingRecord.end) {
                    res.end = res.end?.set({
                        hour: existingRecord.end.hour,
                        minute: existingRecord.end.minute,
                    });
                }
            }
            res.id = existingRecord.id;
        }
        return res;
    }

    /**
     * @override
     */
    getPopoverProps(record) {
        record = record?.rawRecord;
        return {
            readonly: !this.props.editRecord,
            onReload: async () => await this.props.model.load(),
            originalRecord: record,
            editArchInfo: this.editArchInfo,
            getDurationStr: (duration) =>
                formatFloatTime(duration, {
                    noLeadingZeroHour: true,
                }).replace(/(:00|:)/g, "h"),
            recordProps: this.resourcePopoverService.recordProps,
            archInfo: this.resourcePopoverService.archInfo,
            context: this.props.model.meta.context,
        };
    }
}
