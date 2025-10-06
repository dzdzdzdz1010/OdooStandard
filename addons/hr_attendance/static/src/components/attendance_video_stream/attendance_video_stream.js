import { Component, onMounted, onWillDestroy, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class AttendanceVideoStream extends Component {
    static template = "hr_attendance.attendance_video_stream";
    static props = {};

    setup() {
        this.notification = useService("notification");

        onWillStart(async () => {
            try {
                await this.startCamera();
            } catch (error) {
                this.stream = null;
                this.notification.add(_t(error.message), {
                    title: _t("Camera Error"),
                    type: "warning",
                });
            }
        });
        onMounted(async () => {
            this.video = document.getElementById("attendance_video_stream");
            await this.startStream();
        });
        onWillDestroy(async () => {
            if (this.video && this.stream) {
                const tracks = this.stream.getTracks();
                tracks.forEach((track) => track.stop());
            }
        });
    }

    async startCamera() {
        this.stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 480 },
                height: { ideal: 480 },
            },
            audio: false,
        });
    }

    async startStream() {
        if (this.video && this.stream) {
            this.video.srcObject = this.stream;
            await this.video.play();
        }
    }
}
