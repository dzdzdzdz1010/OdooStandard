import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

export class RecordingDialog extends Component {
    static template = "discuss.RecordingDialog";
    static props = [ "close" ];
    static components = { Dialog };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.state = useState({
            audio: false,
            video: false,
            transcription: false,
        });
    }

    get recordingButtonText() {
        if (this.store.rtc?.recordingState.recording) {
            return "Stop recording";
        }
        return "Start recording";
    }

    onClickRecording() {
        if (this.store.rtc?.recordingState.recording) {
            this.store.rtc.stopRecordingDebounce();
        } else {
            this.store.rtc.startRecordingDebounce({
                audio: this.state.audio,
                transcription: this.state.transcription,
                video: this.state.video
            });
        }
        this.props.close();
    }
}
