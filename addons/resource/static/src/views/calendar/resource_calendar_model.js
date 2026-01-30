import { CalendarModel } from "@web/views/calendar/calendar_model";
import { deserializeDate } from "@web/core/l10n/dates";

export class ResourceCalendarModel extends CalendarModel {
    _combineDate(date, floatTime) {
        const hours = Math.floor(floatTime);
        const minutes = Math.round((floatTime - hours) * 60);
        return date.set({
            hour: hours,
            minute: minutes,
        });
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
}
