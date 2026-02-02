import { useService } from "@web/core/utils/hooks";
import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class ActivityCalendarYearPopover extends CalendarYearPopover {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    onRecordClick(record) {
        this.actionService.doActionButton({
            type: "object",
            name: "action_open_document",
            resModel: "mail.activity",
            resId: record.rawRecord.id,
            onClose: () => this.props.model.load(),
        });
        this.props.close();
    }
}
