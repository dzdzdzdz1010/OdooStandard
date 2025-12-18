import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { serializeDate } from "@web/core/l10n/dates";
import { Cache } from "@web/core/utils/cache";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, {
    setup() {
        super.setup(...arguments);
        this.data.workingHours = {};
        this._unusualDaysCache = new Cache(
            (data) => this.fetchUnusualDays(data),
            (data) => {
                const startDate = serializeDate(data.range.start);
                const endDate = serializeDate(data.range.end);
                const activePartnerIds = data.filterSections.partner_ids?.filters
                    .filter((partner) => partner.active)
                    .map((partner) => partner.value)
                    .sort()
                    .join(",");
                return `${startDate},${endDate},${activePartnerIds}`;
            }
        );
    },

    get workingHours() {
        return this.data.workingHours;
    },

    get unusualDays() {
        // If the calendar has working hours AND the calendar is viewed in "day" or "week" view, the working hours
        // should include all the days that are in unusualDays so displaying unusual days is redundant.
        const hasWorkingHours = this.data.workingHours.length > 0;
        if (this.meta.scale === "day" || this.meta.scale === "week") {
            return hasWorkingHours ? [] : this.data.unusualDays;
        } else {
            return this.data.unusualDays;
        }
    },

    async updateData(data) {
        await super.updateData(...arguments);
        data.workingHours = await this.fetchWorkingHours(data);
    },

    async fetchWorkingHours(data) {
        if (this.meta.scale !== "day" && this.meta.scale !== "week") {
            return [];
        }
        const activePartnerIds = data.filterSections.partner_ids?.filters
            .filter((partner) => partner.active)
            .map((partner) => partner.value);

        return this.orm.call("res.partner", "get_working_hours_for_all_attendees", [
            activePartnerIds,
            serializeDate(data.range.start),
            serializeDate(data.range.end),
        ]);
    },

    fetchUnusualDays(data) {
        if (this.meta.scale !== "month" && this.meta.scale !== "year") {
            return [];
        }
        // Update unusualDays to also include the days an employee is not available based on their working schedule.
        const activePartnerIds = data.filterSections.partner_ids?.filters
            .filter((partner) => partner.active)
            .map((partner) => partner.value);

        return this.orm.call(this.meta.resModel, "get_unusual_days", [
            serializeDate(data.range.start),
            serializeDate(data.range.end),
            activePartnerIds,
        ]);
    },
});
