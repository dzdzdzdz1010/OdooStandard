/** @odoo-module **/
import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";
import { ResourceCalendarRenderer } from "./resource_calendar_renderer";
import { ResourceCalendarModel } from "./resource_calendar_model";
import { ResourceCalendarController } from "./resource_calendar_controller";

export const ResourceCalendarView = {
    ...calendarView,
    Controller: ResourceCalendarController,
    Renderer: ResourceCalendarRenderer,
    Model: ResourceCalendarModel,
};

registry.category("views").add("resource_calendar", ResourceCalendarView);
