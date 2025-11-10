import { Component, onWillStart, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { BreakDurationDialog } from "@hr_attendance/components/break_duration_dialog/break_duration_dialog";
const { DateTime } = luxon;

export class ActivityMenu extends Component {
    static components = {Dropdown, DropdownItem};
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.lazySession = useService("lazy_session");
        this.employee = false;
        this.state = useState({
            checkedIn: false,
            isDisplayed: false
        });
        this.date_formatter = registry.category("formatters").get("float_time")
        this.dropdown = useDropdownState();
        onWillStart(()=> {
            // access lazy session but do no wait for it, to prevent from delaying the whole webclient
            this.lazySession.getValue("attendance_user_data", (employee) => {
                if (employee) {
                    this.employee = employee;
                    this._searchReadEmployeeFill();
                }
            });
        });
    }

    async searchReadEmployee(){
        this.employee = await rpc("/hr_attendance/attendance_user_data");
        this._searchReadEmployeeFill();
    }

    _searchReadEmployeeFill() {
        if (this.employee.id) {
            this.hoursToday = this.date_formatter(
                this.employee.hours_today
            );
            this.hoursPreviouslyToday = this.date_formatter(
                this.employee.hours_previously_today
            );
            this.lastAttendanceWorkedHours = this.date_formatter(
                this.employee.last_attendance_worked_hours
            );
            this.lastCheckIn = deserializeDateTime(this.employee.last_check_in).toLocaleString(DateTime.TIME_SIMPLE);
            this.state.checkedIn = this.employee.attendance_state === "checked_in";
            this.isFirstAttendance = this.employee.hours_previously_today === 0;
            this.state.isDisplayed = this.employee.display_systray
        } else {
            this.state.isDisplayed = false
        }
    }

    async signInOut() {
        this.dropdown.close();
        await this.searchReadEmployee();
        if (!this.employee || !this.employee.id) {
            return;
        }
        let breakDurationHours = null;
        if (this.employee && this.employee.break_management_enabled && this.employee.attendance_state === "checked_in") {
            const minutes = await this.requestBreakDuration();
            if (minutes === null) {
                return;
            }
            breakDurationHours = (Number(minutes) || 0) / 60;
        }
        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (trackingEnabled && !isIosApp() && navigator.geolocation) {
            // iOS app lacks permissions to call `getCurrentPosition`
            navigator.geolocation.getCurrentPosition(
                async ({coords: {latitude, longitude}}) => {
                    this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                        latitude,
                        longitude,
                        break_duration: breakDurationHours,
                    })
                    this._searchReadEmployeeFill();
                },
                async err => {
                    this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                        break_duration: breakDurationHours,
                    })
                    this._searchReadEmployeeFill();
                },
                {
                    enableHighAccuracy: true,
                }
            )
        } else {
            this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                break_duration: breakDurationHours,
            })
            this._searchReadEmployeeFill();
        }
    }

    async requestBreakDuration() {
        return new Promise((resolve) => {
            let settled = false;
            const finalize = (value) => {
                if (!settled) {
                    settled = true;
                    resolve(value);
                }
            };
            this.dialog.add(BreakDurationDialog, {
                employeeName: this.employee?.employee_name,
                defaultMinutes: 0,
                onConfirm: (minutes) => finalize(minutes),
                onCancel: () => finalize(null),
            });
        });
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
