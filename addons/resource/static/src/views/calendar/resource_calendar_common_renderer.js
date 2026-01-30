import { convertRecordToEvent } from "@web/views/calendar/utils";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";
import { ResourcePopover } from "../../components/resource_popover/resource_popover";
import {serializeDate} from "@web/core/l10n/dates";

export class ResourceCalendarCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer,
        Popover: ResourcePopover,
    };

    setup() {
        super.setup();
        this.resourcePopoverService = useService("resourcePopoverService");
        this.resourcePopoverService.setup(this.props.model.meta, this.additionalFieldsToFetch);
    }

    get additionalFieldsToFetch() {
        return [
            { name: "calendar_id", type: "many2one", readonly: false },
            { name: "date", type: "date", readonly: false },
            { name: "duration_based", type: "boolean", readonly: false },
        ];
    }

    async onSelect(info) {
        const start = luxon.DateTime.fromJSDate(info.start)
        const end = luxon.DateTime.fromJSDate(info.end)
        this.popover.open(
            info.jsEvent.toElement,
            this.getPopoverProps({rawRecord: {
                    date: serializeDate(start),
                    hour_from: start.hour+start.minute/60,
                    hour_to: end.hour+end.minute/60,
                }}),
            `o_cw_popover card o_calendar_color_0`
        );
    }

    /**
     * @override
     */
    convertRecordToEvent(record) {
        const event = convertRecordToEvent(record);
        const editable = record.rawRecord.state !== "validated" && (event.editable ?? null);
        return {
            ...event,
            ...(editable ? { editable: editable } : {}),
        };
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
        };
    }
}
