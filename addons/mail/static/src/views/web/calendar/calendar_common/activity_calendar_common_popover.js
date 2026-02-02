import { useService } from "@web/core/utils/hooks";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

export class ActivityCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "mail.ActivityCalendarCommonPopover.footer",
    };
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    openRecord() {
        this.actionService.doActionButton({
            type: "object",
            name: "action_open_document",
            resModel: "mail.activity",
            resId: this.props.record.rawRecord.id,
            onClose: () => this.props.model.load(),
        });
        this.props.close();
    }
}
