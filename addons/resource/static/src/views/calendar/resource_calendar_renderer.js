import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { ResourceCalendarCommonRenderer } from "./resource_calendar_common_renderer";

export class ResourceCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        week: ResourceCalendarCommonRenderer,
        month: ResourceCalendarCommonRenderer,
    };
}
