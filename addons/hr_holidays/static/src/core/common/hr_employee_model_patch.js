import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/model/misc";
import { HrEmployee } from "@hr/core/common/hr_employee_model";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

patch(HrEmployee.prototype, {
    setup() {
        super.setup();
        this.leave_date_to = fields.Date();
        this.leave_date_from = fields.Datetime();
        /** @type {'am'|pm} */
        this.request_date_from_period;
    },
    get outOfOfficeDateEndText() {
        if (!this.leave_date_to && !this.leave_date_from) {
            return "";
        }
        if (
            DateTime.now().hasSame(this.leave_date_from, "day") &&
            (this.request_date_from_period === "pm" || this.leave_date_from.hour > 12)
        ) {
            const time = this.leave_date_from.toLocaleString(DateTime.TIME_SIMPLE);
            return _t("Out of office starting at %(time)s", { time });
        }
        if (DateTime.now().plus({ day: 1 }).hasSame(this.leave_date_from, "day")) {
            // A negative diff means the leave period is ongoing.
            return _t("Out of office tomorrow");
        }
        const foptions = { ...DateTime.DATE_MED };
        if (DateTime.now().hasSame(this.leave_date_to, "year")) {
            foptions.year = undefined;
        }
        const date = this.leave_date_to.toLocaleString(foptions);
        return _t("Back on %(date)s", { date });
    },
});
