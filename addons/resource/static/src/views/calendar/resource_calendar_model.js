import { CalendarModel } from "@web/views/calendar/calendar_model";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";

export class ResourceCalendarModel extends CalendarModel {
    _combineDate(date, floatTime) {
        const hours = Math.floor(floatTime);
        const minutes = Math.round((floatTime - hours) * 60);
        return date.set({
            hour: hours,
            minute: minutes,
        });
    }

    get hasMultiCreate() {
        return !!this.meta.multiCreateView && !this.env.isSmall && ["week", "month"].includes(this.meta.scale);
    }

    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        const res = super.normalizeRecord(rawRecord);
        const { fieldMapping } = this.meta;

        const isAllDay = (fieldMapping.all_day && rawRecord[fieldMapping.all_day]) || false;
        if (isAllDay) {
            return res;
        }
        const start = this._combineDate(
            deserializeDate(rawRecord[fieldMapping.date_start]),
            rawRecord.hour_from
        );
        const end = this._combineDate(
            deserializeDate(rawRecord[fieldMapping.date_start]),
            rawRecord.hour_to
        );
        const duration = end.diff(start, "hours").hours;

        return {
            ...res,
            isAllDay,
            start,
            startType: "datetime",
            end,
            endType: "datetime",
            duration,
            showTime: true,
        };
    }

    buildRawRecord(partialRecord, options = {}) {
        const data = super.buildRawRecord(...arguments);
        let start = partialRecord.start;
        let end = partialRecord.end;
        data[this.meta.fieldMapping.date_start] = serializeDate(start)
        debugger
        if (!partialRecord.isAllDay || !this.hasAllDaySlot){
            data["hour_from"] = start?.hour+start?.minute/60
            data["hour_to"] = end?.hour+end?.minute/60
        }
        return data;
    }
}
