import { Component, onWillStart, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isIosApp } from "@web/core/browser/feature_detection";
import { AttendanceVideoStream } from "../attendance_video_stream/attendance_video_stream";
const { DateTime } = luxon;

export class ActivityMenu extends Component {
    static components = { Dropdown, DropdownItem, AttendanceVideoStream };
    static props = [];
    static template = "hr_attendance.attendance_menu";

    setup() {
        this.ui = useService("ui");
        this.lazySession = useService("lazy_session");
        this.employee = false;
        this.state = useState({
            checkedIn: false,
            isDisplayed: false
        });
        this.date_formatter = registry.category("formatters").get("float_time")
        this.dropdown = useDropdownState();
        onWillStart(() => {
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
            this.state.isDisplayed = this.employee.display_systray;
            this.state.displayVideoStream = this.employee.capture_check_in_picture && !this.state.checkedIn;
        } else {
            this.state.isDisplayed = false;
        }
    }

    async _capturePicture() {
        const canvas = document.createElement("canvas");
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);

        const imgData = canvas.toDataURL("image/webp");
        return imgData.split(",")[1];
    }

    async signInOut() {
        let latitude = false;
        let longitude = false;
        let check_in_image = null;

        this.video = document.getElementById("attendance_video_stream");
        if (this.video && this.video.srcObject) {
            check_in_image = await this._capturePicture();
            this.video.srcObject.getTracks().forEach((track) => track.stop());
        }

        this.dropdown.close();

        const sendAttendanceData = async () => {
            this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
                check_in_image,
            });
            this._searchReadEmployeeFill();
        };

        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (trackingEnabled && !isIosApp() && navigator.geolocation) {
            // iOS app lacks permissions to call `getCurrentPosition`
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude: lat, longitude: lon } }) => {
                    latitude = lat;
                    longitude = lon;
                    await sendAttendanceData();
                },
                async (err) => {
                    await sendAttendanceData();
                },
                {
                    enableHighAccuracy: true,
                }
            );
        } else {
            await sendAttendanceData();
        }
    }
}

export const systrayAttendance = {
    Component: ActivityMenu,
};

registry
    .category("systray")
    .add("hr_attendance.attendance_menu", systrayAttendance, { sequence: 101 });
